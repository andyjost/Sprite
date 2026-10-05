#pragma once
#include "boost/utility.hpp"
#include "cyrt/fwd.hpp"
#include "cyrt/state/configuration.hpp"
#include <deque>
#include <memory>

namespace cyrt
{
  using queue_type = std::deque<Configuration*>;

  // A queue of configurations.  The queue owns its configurations: pop_front
  // lets go of the front one, and the destructor of the rest, and the last
  // queue to let go of a configuration destroys it (Configuration::holders
  // counts the queues).  A configuration is in two queues only after split,
  // and a queue clones such a configuration before it evaluates it
  // (unshare_front), so no queue sees the steps of another.
  //
  // The outermost queue of an evaluation belongs to its runtime state.  The
  // queue of a set function belongs to its SetEval node, and a copy of that
  // node shares the queue, so the collector frees it: every queue registers
  // itself (gc_register_queue), the mark phase marks the queues it reaches,
  // and the sweep destroys the rest.  See gc/wdgc.cpp.
  struct Queue : boost::noncopyable
  {
    Queue(Set * set=nullptr, Node * root=nullptr);
    ~Queue();

    Set * set;
    // The serial number of the queue, unique in the process.  The trace keys
    // its tables by it, so a queue at the address of a dead one starts
    // fresh.
    size_t const serial;
    // The mark of the current collection.  See gc/wdgc.cpp.
    bool marked = false;
    // The SetEval nodes that refer to this queue, counted by the MPS back
    // end (gc/mps.cpp), which destroys the queue when the last of them has
    // died.  Unused by the default collector.
    size_t seteval_refs = 0;

    using iterator = queue_type::iterator;
    using const_iterator = queue_type::const_iterator;
    iterator begin() { return this->items.begin(); }
    iterator end() { return this->items.end(); }
    const_iterator begin() const { return this->items.begin(); }
    const_iterator end() const { return this->items.end(); }
    // The size is kept in a counter: the scheduler asks for it at every
    // step (count_step), and the size of a deque is an arithmetic over its
    // iterators.
    bool empty() const { return this->count == 0; }
    size_t size() const { return this->count; }
    Configuration * front() const { return this->items.front(); }

    void push_back(std::unique_ptr<Configuration>);
    void push_front(std::unique_ptr<Configuration>);
    // Lets go of the front configuration.  It is destroyed unless another
    // queue holds it.
    void pop_front();
    // Moves the front configuration to the back.
    void rotate();
    // Makes the front configuration private to this queue: a configuration
    // another queue holds too is replaced by a clone.  Returns the front.
    // The scheduler calls this before it reads or steps the front.
    Configuration * unshare_front()
    {
      Configuration * C = this->items.front();
      return C->holders > 1 ? this->clone_front() : C;
    }
    // Splits the queue on choice ``cid``: a configuration that made the
    // choice RIGHT moves to ``rhs``; one that has not made it stays and
    // joins ``rhs`` as well.  ``rhs`` must be empty.
    void split(xid_type cid, Queue & rhs);

  private:
    queue_type items;
    // The number of configurations in ``items``.
    size_t count = 0;
    Configuration * clone_front();
    static void let_go(Configuration *);
  };
}
