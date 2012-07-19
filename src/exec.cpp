/**
 * @file
 * @brief Implements functions related to execution.
 */
#include "sprite/cmdline.hpp"
#include "sprite/exec.hpp"
#include "sprite/node.hpp"
#include "sprite/operators.hpp"
#include <deque>
#include <csetjmp>

namespace
{
  /**
   * @brief The jump buffer used for returning when the available computation
   * steps are exhausted.
   *
   * The setjmp/longjmp functions are not safe in C++!  It is essential that
   * any stack frames skipped in the jump have no local variables with
   * non-trivial desctructors.  Functions that perform some part of a
   * computation (e.g., fair_normalize, head_normalize, generated H functions)
   * should in all cases use global variables instead of local variables.
   */
  jmp_buf g_jmppt;
}

namespace sprite
{
  // Documented in the header.
  Program const * g_program = NULL;
  size_t g_steps;
  void const * g_context;
  Node * g_redex;

  #ifdef SPRITE_USE_POOLING
  /// Global memory pool for allocating nodes.
  boost::pool<> node_allocator(NODE_BYTES);
  
  /// Memory pools for child lists of various length.
  boost::pool<> * init_pool()
  {
    boost::pool<> * p = reinterpret_cast<boost::pool<> *>(
        new char[sizeof(boost::pool<>) * SPRITE_REWRITE_ARG_BOUND]
      );
    #define F(z,i,_) new(&p[i]) boost::pool<>(i * sizeof(NodePtr));
    BOOST_PP_REPEAT(SPRITE_REWRITE_ARG_BOUND,F,)
    #undef F
    return p;
  };
  boost::pool<> * childpool = init_pool();

  #endif

  // Globals used in generated H functions.  g_parent must be declared *after*
  // node_allocator to ensure the proper static destruction order.
  NodePtr g_parent;
  Node * g_inductive;

  void head_normalize(Node * node)
  {
    SPRITE_COUNT(CNT_H);
    switch(node->tag())
    {
      // For operations, call the H function.
      case OPER:
      {
        SPRITE_UNCOUNT(CNT_H);

        // Call the H function.
        loop:
        SPRITE_COUNT(CNT_H);
        g_program->call_h(*node);

        redo: switch(node->tag())
        {
          case FWD: node = node->_fwdtarget().get(); goto redo;
          case OPER: if(--g_steps == 0) longjmp(g_jmppt, 1); goto loop;
          default: if(--g_steps == 0) longjmp(g_jmppt, 1); return;
        }
      }
      break;

      // For non-constructors, throw.
      case FAIL: case CHOICE: case FWD:
        throw RuntimeError(
            "defined operation or constructor expected in "
              + std::string(BOOST_CURRENT_FUNCTION)
          );

      // Ignore constructor types.
      case INT: case FLOAT: case CHAR: case CTOR: default:
        return; // H.6
    }
  }

  namespace 
  {
    /// An item in the computation pool.
    struct PoolItem
    {
      Fingerprint fp;
      NodePtr node;

      PoolItem(Fingerprint const & fp_, NodePtr const & node_)
        : fp(fp_), node(node_)
      {}

      #ifdef SPRITE_USE_POOLING
      /// A memory pool for items in the computation pool.
      static boost::pool<> allocator;
      #endif

      /// Overloaded new that uses the memory pool.
      void * operator new(size_t sz)
      {
        assert(sz == sizeof(PoolItem));
        #ifdef SPRITE_USE_POOLING
        return allocator.malloc();
        #else
        return std::malloc(sizeof(PoolItem));
        #endif
      }

      /// Overloaded delete that uses the memory pool.
      void operator delete(void * p)
      #ifdef SPRITE_USE_POOLING
        // Does not call p's destructor.
        { allocator.free(static_cast<PoolItem*>(p)); }
      #else
        { std::free(p); }
      #endif
    };

    #ifdef SPRITE_USE_POOLING
    // Storage declaration for the above item.
    boost::pool<> PoolItem::allocator(sizeof(PoolItem));
    #endif

    /// A computation pool.
    struct ComputationPool
    {
      /// Push an item onto the end of the computation pool.
      void push(Fingerprint const & fp, NodePtr const & node)
      {
        assert(node);
        PoolItem * x = new PoolItem(fp, node);
        try
          { m_storage.push_back(x); }
        catch(...)
          { delete x; }
      }

      /// Return the item at the front of the computation pool.
      PoolItem & front() { return *m_storage.front(); }
      PoolItem const & front() const { return *m_storage.front(); }

      /// Rotate the front item to the back of the computation pool.
      void rotate()
      {
        assert(!empty());
        m_storage.push_back(m_storage.front());
        m_storage.pop_front();
      }

      /// Pop and discard the item at the front of the computation pool.
      void pop()
      {
        assert(!empty());
        delete m_storage.front();
        m_storage.pop_front();
      }

      /// True if the computation pool is empty.
      bool empty() const { return m_storage.empty(); }

      /// Destroy the computation pool.
      ~ComputationPool()
      {
        BOOST_FOREACH(PoolItem const * item, m_storage)
          { delete item; }
      }
    private:
      typedef std::deque<PoolItem *> storage_type;
      storage_type m_storage;
    };

    /// The normalizing (N) function from the fair scheme.
    void fair_normalize(Fingerprint const & fp, Node * node)
    {
      SPRITE_COUNT(CNT_N);
      redo: switch(node->tag())
      {
        case FWD: node = node->_fwdtarget().get(); goto redo;

        // N.4
        case OPER: return head_normalize(node);

        // N.3 (always a cnf.)
        case INT: case FLOAT: case CHAR: return;

        default:
        {
          // Borrow g_inductive to point to the first choice child (if there is
          // one).
          g_inductive = 0;
          size_t pos = 0;
          BOOST_FOREACH(NodePtr & child, node->iter())
          {
            redo2: switch(child->tag())
            {
              case FWD: child.remove_fwd(); goto redo2;

              // N.1
              case FAIL: return rewrite_fail(*node);
              case CHOICE:
                if(!g_inductive)
                {
                  g_inductive = child.get();
                  pos = node->position(child);
                }
                break;
              // pass other cases.
              default:;
            }
          }

          // N.2
          // If g_inductive was set to something, it is the first choice
          // encountered in the list of children.
          if(g_inductive) return pull_tab(node, g_inductive, pos);

          // N.3
          BOOST_FOREACH(NodePtr & child, node->iter())
            { fair_normalize(fp, child.get()); }
        }
      }
    }

    /**
     * @brief A simplified version of the normalizing (FN) function.
     *
     * This is intended to be a very minimal function to bue used for benchmarking
     * test cases that do not involve failures of choices.
     */
    void fast_normalize(Node * node)
    {
      SPRITE_COUNT(CNT_N);
      redo: switch(node->tag())
      {
        case FWD: node = node->_fwdtarget().get(); goto redo;

        // N.4
        case OPER: return head_normalize(node);

        // N.3 (always a cnf.)
        case INT: case FLOAT: case CHAR: return;

        default:
          // N.3
          BOOST_FOREACH(NodePtr & child, node->iter())
            { fast_normalize(child.get()); }
      }
    }
  }

  /// Prints a trace message to the output.
  static void tracef(std::string const & tag, Node const & expr)
    { std::cout << "TRACE> " << tag << ":: " << expr << std::endl; }

  // See header for brief description.
  void execute(
      Program const & pgm, Node & goal, CmdlineOptions const & opt
    , YieldHandler const & out
    )
  {
    if(opt.grain==0)
      throw RuntimeError("a granularity of zero steps was specified");

    // Set the global program pointer and then restore it when this scope
    // exits.
    Program const * _p = &pgm;
    std::swap(g_program, _p);
    BOOST_SCOPE_EXIT((&_p)) { std::swap(g_program, _p); } BOOST_SCOPE_EXIT_END

    // If tracing, set the output program.  Restore the old value when this
    // scope exits.
    Program const * _pp = manipulators::detail::pgm_data(std::cout);

    if(opt.trace)
      std::cout << setprogram(pgm);

    BOOST_SCOPE_EXIT((&_pp))
      // TODO !! Can _pp be NULL ? !!
      { std::cout << setprogram(*_pp); }
    BOOST_SCOPE_EXIT_END

    // Clear the counters.
    #ifdef SPRITE_USE_COUNTING
    std::fill_n(&g_counts[0], (size_t)(CNT_END), 0);
    #endif

    if(opt.fastnormalize)
    {
      g_steps = opt.grain;
      fast_normalize(&goal);
      return;
    }

    // Set up the computation pool.
    ComputationPool pool;
    pool.push(Fingerprint(), NodePtr(&goal));

    while(!pool.empty())
    {
      PoolItem & item = pool.front();
      Fingerprint const & fp = item.fp;

      // Reset the number of allowed steps before calling fair_normalize.
      g_steps = opt.grain;

      // Perform some computation steps.  If fair_normalize exhausts its
      // allotment of steps, it will return through setjmp with a nonzero
      // value.
      if(setjmp(g_jmppt) == 0)
        fair_normalize(item.fp, item.node.get());

      // This dereference will remove FWD nodes (it must come after the
      // execution step, above).
      Node & node = *item.node.remove_fwd();
      if(opt.trace) tracef("step", node);

      if(node.is_cnf())
      {
        if(opt.trace) tracef("value", node);
        out.yield(node);
        pool.pop();
      }
      else
      {
        switch(node.tag())
        {
          case FAIL:
            if(opt.trace) tracef("fail", node);
            pool.pop();
            break;
          case CHOICE:
          {
            if(opt.trace) tracef("choice", node);
            size_t const id = node.id();
            if(fp.has(id))
            {
              // Recycle the current front of the computation pool (since it is
              // being killed, and its replacement uses the same fingerprint).
              // Change its node pointer, then rotate it to the back of the pool.
              assert(fp.at(id) == 0 || fp.at(id) == 1);
              item.node = node[fp.at(id)];
              pool.rotate();
            }
            else
            {
              Fingerprint fpl = fp;
              if(fpl.size() <= id) { fpl.resize(id); }
              fpl.set(id, LEFT);
              pool.push(fpl, node[LEFT]);

              Fingerprint fpr = fp;
              if(fpr.size() <= id) { fpr.resize(id); }
              fpr.set(id, RIGHT);
              pool.push(fpr, node[RIGHT]);

              pool.pop();
            }
            break;
          }
          default: pool.rotate(); break;
        }
      }
    }

    // Print the counters.
    #ifdef SPRITE_USE_COUNTING
    std::cout << "============ Event Counts ============\n"
                 "  Fair Normalize (N): " << g_counts[CNT_N] << "\n"
                 "  Head Normalize (H): " << g_counts[CNT_H] << "\n"
                 "  Rewrite:            " << g_counts[CNT_RW] << "\n"
                 "  Create:             " << g_counts[CNT_CR] << "\n"
                 "  Pull-Tab:           " << g_counts[CNT_PT] << "\n"
                 "======================================\n"
                 << std::endl;
    #endif
  }

  void print_node(Node const & node)
    { std::cout << node << std::endl; }
}
