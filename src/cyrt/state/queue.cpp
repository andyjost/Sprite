#include <cassert>
#include "cyrt/graph/memory.hpp"
#include "cyrt/state/queue.hpp"
#include <vector>

namespace cyrt
{
  static size_t g_queue_serial = 0;

  Queue::Queue(Set * set, Node * root)
    : set(set), serial(g_queue_serial++)
  {
    gc_register_queue(this);
    try
    {
      if(root)
        this->push_back(Configuration::create(root));
    }
    catch(...)
    {
      gc_unregister_queue(this);
      throw;
    }
  }

  Queue::~Queue()
  {
    for(Configuration * C: this->items)
      Queue::let_go(C);
    gc_unregister_queue(this);
  }

  void Queue::let_go(Configuration * C)
  {
    assert(C->holders > 0);
    if(--C->holders == 0)
      delete C;
  }

  void Queue::push_back(std::unique_ptr<Configuration> C)
  {
    assert(C && C->holders == 0);
    this->items.push_back(C.get());
    ++this->count;
    C.release()->holders = 1;
  }

  void Queue::push_front(std::unique_ptr<Configuration> C)
  {
    assert(C && C->holders == 0);
    this->items.push_front(C.get());
    ++this->count;
    C.release()->holders = 1;
  }

  void Queue::pop_front()
  {
    assert(!this->items.empty());
    Configuration * C = this->items.front();
    this->items.pop_front();
    --this->count;
    Queue::let_go(C);
  }

  void Queue::rotate()
  {
    assert(!this->items.empty());
    this->items.push_back(this->items.front());
    this->items.pop_front();
  }

  Configuration * Queue::clone_front()
  {
    Configuration * C = this->items.front();
    assert(C->holders > 1);
    auto clone = C->clone(*C->root);
    // Nothing below throws.
    --C->holders;
    C = clone.release();
    C->holders = 1;
    this->items.front() = C;
    return C;
  }

  void Queue::split(xid_type cid, Queue & rhs)
  {
    assert(rhs.empty());
    queue_type keep, move;
    std::vector<Configuration *> shared;
    for(Configuration * C: this->items)
    {
      switch(C->fingerprint.test(cid))
      {
        case LEFT:         keep.push_back(C);
                           break;
        case RIGHT:        move.push_back(C);
                           break;
        case UNDETERMINED: keep.push_back(C);
                           move.push_back(C);
                           shared.push_back(C);
                           break;
      }
    }
    // Nothing below throws.
    this->items.swap(keep);
    rhs.items.swap(move);
    this->count = this->items.size();
    rhs.count = rhs.items.size();
    for(Configuration * C: shared)
      ++C->holders;
  }
}
