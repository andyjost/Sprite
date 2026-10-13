#include <algorithm>
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

  // Whether C made choice ``cid``: its own fingerprint, read as read_fp
  // reads it, through the group.
  static ChoiceState decision(Configuration const * C, xid_type cid)
  {
    return C->fingerprint.test(C->grp_id(cid));
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

  bool Queue::decided(xid_type cid) const
  {
    return std::find(this->decisions.begin(), this->decisions.end(), cid)
        != this->decisions.end();
  }

  void Queue::split(xid_type cid, Queue & rhs)
  {
    assert(rhs.empty());
    queue_type keep, move;
    std::vector<Configuration *> shared;
    for(Configuration * C: this->items)
    {
      switch(decision(C, cid))
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
    std::vector<xid_type> decisions = this->decisions;
    decisions.push_back(cid);
    std::vector<xid_type> rhs_decisions = decisions;
    BindingMap rhs_absorbed = this->absorbed;
    std::vector<FailureRecord> rhs_failures = this->outside_failures;
    // Nothing below throws.
    this->items.swap(keep);
    rhs.items.swap(move);
    this->count = this->items.size();
    rhs.count = rhs.items.size();
    this->decisions.swap(decisions);
    rhs.decisions.swap(rhs_decisions);
    rhs.absorbed.swap(rhs_absorbed);
    rhs.produced = this->produced;
    rhs.inside_failure = this->inside_failure;
    rhs.outside_failures.swap(rhs_failures);
    for(Configuration * C: shared)
      ++C->holders;
  }

  void Queue::clone(Queue & copy, xid_type vid, Node * binding)
  {
    assert(copy.empty());
    queue_type items = this->items;
    std::vector<xid_type> decisions = this->decisions;
    BindingMap absorbed = this->absorbed;
    absorbed[vid] = binding;
    std::vector<FailureRecord> failures = this->outside_failures;
    // Nothing below throws.
    copy.items.swap(items);
    copy.count = copy.items.size();
    copy.decisions.swap(decisions);
    copy.absorbed.swap(absorbed);
    copy.produced = this->produced;
    copy.inside_failure = this->inside_failure;
    copy.outside_failures.swap(failures);
    for(Configuration * C: copy.items)
      ++C->holders;
  }

  // The level choice of rule (d3); see the declaration.
  std::vector<Set *> failure_guards(std::vector<FailureRecord> const & records)
  {
    std::vector<Set *> guards;
    if(records.empty())
      return guards;
    size_t least = records.front().level;
    for(FailureRecord const & record: records)
      least = std::min(least, record.level);
    for(FailureRecord const & record: records)
      if(record.level == least)
        for(Set * set: record.guards)
          if(std::find(guards.begin(), guards.end(), set) == guards.end())
            guards.push_back(set);
    return guards;
  }

  std::vector<Set *> Queue::failure_guards() const
  {
    return cyrt::failure_guards(this->outside_failures);
  }
}
