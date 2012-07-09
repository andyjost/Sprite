/**
 * @file
 * @brief Implements functions related to execution.
 */
#include "sprite/exec.hpp"
#include "sprite/node.hpp"
#include "sprite/operators.hpp"
#include <deque>

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
        g_program->call_h(*node);
        SPRITE_COUNT(CNT_H);

        switch(node->tag())
        {
          case FWD: node = node->_fwdtarget().get(); break;
          case OPER: if(--g_steps) goto loop; break;
          default: --g_steps; return;
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
      switch(node->tag())
      {
        case OPER:
          return head_normalize(node);

        case INT: // Always a cnf.
        case FLOAT: // Always a cnf.
        case CHAR: // Always a cnf.
          return;

        default:
        {
          // TODO: must rewrite this section to match the paper.  In
          // particular, the choice and fail rules must be applied BEFORE any
          // recursive calls to fair_normalize.
          BOOST_FOREACH(NodePtr & child, node->iter())
          {
            switch(child->tag())
            {
              case FAIL: return rewrite_fail(*node);
              case OPER: head_normalize(child.get()); break;
              case CHOICE: return pull_tab(*node, child);
              case INT: case FLOAT: case CHAR: break;
              case FWD: throw RuntimeError("Unexpected FWD node.");
              default: case CTOR:
                assert(child->tag() >= CTOR);
                fair_normalize(fp, child.get());
            }
          }
        }
      }
    }
  }

  /// Prints a trace message to the output.
  static void tracef(std::string const & tag, Node const & expr)
    { std::cout << "TRACE> " << tag << ":: " << expr << std::endl; }

  // See header for brief description.
  void execute(
      Program const & pgm, Node & goal, size_t grain
    , YieldHandler const & out, TraceOption trace
    )
  {
    if(grain==0)
      throw RuntimeError("a granularity of zero steps was specified");

    // Set the global program pointer and then restore it when this scope
    // exits.
    Program const * _p = &pgm;
    std::swap(g_program, _p);
    BOOST_SCOPE_EXIT((&_p)) { std::swap(g_program, _p); } BOOST_SCOPE_EXIT_END

    // If tracing, set the output program.  Restore the old value when this
    // scope exits.
    Program const * _pp = manipulators::detail::pgm_data(std::cout);

    if(trace)
      std::cout << setprogram(pgm);

    BOOST_SCOPE_EXIT((&_pp))
      // TODO !! Can _pp be NULL ? !!
      { std::cout << setprogram(*_pp); }
    BOOST_SCOPE_EXIT_END

    // Clear the counters.
    #ifdef SPRITE_USE_COUNTING
    std::fill_n(&g_counts[0], (size_t)(CNT_END), 0);
    #endif

    // Set up the computation pool.
    ComputationPool pool;
    pool.push(Fingerprint(), NodePtr(&goal));

    while(!pool.empty())
    {
      PoolItem & item = pool.front();
      Fingerprint const & fp = item.fp;

      // Reset the number of allowed steps before calling fair_normalize.
      g_steps = grain;

      // Perform some computation steps.
      fair_normalize(item.fp, item.node.get());

      // This dereference will remove FWD nodes (it must come after the
      // execution step, above).
      Node & node = *item.node;
      if(trace) tracef("step", node);

      if(node.is_cnf())
      {
        if(trace) tracef("value", node);
        out.yield(node);
        pool.pop();
      }
      else
      {
        switch(node.tag())
        {
          case FAIL:
            if(trace) tracef("fail", node);
            pool.pop();
            break;
          case CHOICE:
          {
            if(trace) tracef("choice", node);
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
