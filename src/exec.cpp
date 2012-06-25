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

  #ifdef SPRITE_USE_POOLING
  /// Global memory pool for allocating nodes.
  boost::object_pool<AbstractNode> node_allocator;
  #endif

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
      static boost::object_pool<PoolItem> allocator;
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
    boost::object_pool<PoolItem> PoolItem::allocator;
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
  }

  /// Prints a trace message to the output.
  static void tracef(std::string const & tag, Node const & expr)
    { std::cout << "TRACE> " << tag << ":: " << expr << std::endl; }

  // See header for brief description.
  void execute(
      Program const & pgm, Node & goal, YieldHandler const & out
    , TraceOption trace
    )
  {
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

    // Set up the computation pool.
    ComputationPool pool;
    pool.push(Fingerprint(), NodePtr(&goal));

    while(!pool.empty())
    {
      PoolItem & item = pool.front();
      Fingerprint const & fp = item.fp;

      fair_normalize(item.fp, *item.node);

      // This dereference will remove FWD nodes (it must come after the
      // execution step, above).
      Node & node = *item.node;
      if(trace) tracef("step", node);

      if(is_norm(node))
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
  }

  void print_node(Node const & node)
    { std::cout << node << std::endl; }
}
