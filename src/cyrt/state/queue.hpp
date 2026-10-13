#pragma once
#include "cyrt/fwd.hpp"
#include "cyrt/state/configuration.hpp"
#include <deque>
#include <memory>
#include <vector>

namespace cyrt
{
  using queue_type = std::deque<Configuration*>;

  // A recorded outside failure of a capsule: rule (d1) of the failure rule
  // F2 in its deferred form (Definition 2.94 of the note on the Fair
  // Scheme; see RuntimeState::record_failure).  ``level`` is the position,
  // in the chain of the capsules innermost first, of the outermost capsule
  // whose guard the failure crossed: the level at which the failed cell
  // entered the chain.  Zero names the capsule itself: the failure crossed
  // the guard of its own argument alone.  ``guards`` are the sets of the
  // enclosing guards the failure crossed, less the set of the capsule.
  struct FailureRecord
  {
    size_t level;
    std::vector<Set *> guards;
  };

  // Rule (d3) of the failure rule F2: the guards of the failure a capsule
  // with the outside failures ``records`` becomes.  This is the one place
  // that chooses the records: the records at the least level (the
  // failures that entered the chain innermost; deviation 147 of the
  // README of the Lean development), and the union of their guards.  A
  // record of level zero makes a plain failure, which escapes to no
  // enclosing capsule.  Queue::failure_guards and the checker
  // (Checker::check_capsule_end) call it.
  std::vector<Set *> failure_guards(std::vector<FailureRecord> const & records);

  // A queue of configurations.  The queue owns its configurations: pop_front
  // lets go of the front one, and the destructor of the rest, and the last
  // queue to let go of a configuration destroys it (Configuration::holders
  // counts the queues).  A configuration is in two queues only after the
  // escape of a choice from a set function (split) or the clone of a
  // capsule for a configuration whose binding it read (clone), and a queue
  // clones such a configuration before it evaluates it (unshare_front), so
  // no queue sees the steps of another.
  //
  // The outermost queue of an evaluation belongs to its runtime state.  The
  // queue of a set function belongs to its SetEval node, and a copy of that
  // node shares the queue, so the collector frees it: every queue registers
  // itself (gc_register_queue), the mark phase marks the queues it reaches,
  // and the sweep destroys the rest.  See gc/wdgc.cpp.
  struct Queue
  {
    Queue(Set * set=nullptr, Node * root=nullptr);
    ~Queue();
    Queue(Queue const &) = delete;
    Queue & operator=(Queue const &) = delete;

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
    // The choices whose escapes made this queue (split).  A configuration
    // of the queue does not escape such a choice again
    // (RuntimeState::choice_escapes): it forks on it, and the fork reads the
    // side from its own fingerprint, or from the fingerprint of the
    // enclosing configuration, which runs this queue because it decided the
    // choice that way (read_fp).  So the side is written into no nested
    // fingerprint.  The queues of a split share the choices escaped before
    // it.
    std::vector<xid_type> decisions;
    // Whether choice ``cid`` is in ``decisions``.
    bool decided(xid_type cid) const;
    // The bindings of enclosing configurations that the nested evaluation
    // of this queue reads: the state of the capsule, keyed by the group id
    // of the variable in the configurations of the queue.  A capsule whose
    // evaluation reads a binding of the configuration that runs it depends
    // on the private state of that configuration, so the queue is cloned
    // for it, and the clone absorbs the binding (RuntimeState::diverge;
    // allValues_step in currylib/setfunctions.cpp).  The queues of a split
    // and the clones of a queue share the bindings absorbed before.  The
    // readers (RuntimeState::get_binding) look here after the map of the
    // configuration and before the enclosing configurations.
    BindingMap absorbed;
    // The failure record of the capsule (Definition 2.94, the deferred form
    // of the failure rule F2; RuntimeState::record_failure writes it, and
    // allValues_step in currylib/setfunctions.cpp reads it on the empty
    // queue).  ``produced`` counts the values the queue gave (rule SF.3),
    // ``inside_failure`` tells whether a configuration met a failure of the
    // function's own, and ``outside_failures`` are the failures that came
    // from an argument, each with its level.  The queues of a split and the
    // clones of a queue share the record made before, as the mechanization
    // keeps it (Capsule.split and the clone of the Lean development).
    size_t produced = 0;
    bool inside_failure = false;
    std::vector<FailureRecord> outside_failures;
    // Rule (d2): on the empty queue the capsule is a failure when it
    // produced no value, recorded no inside failure and recorded some
    // outside failure; its set stands otherwise.
    bool fails_at_end() const
    {
      return this->produced == 0 && !this->inside_failure
          && !this->outside_failures.empty();
    }
    // Rule (d3): the guards of the failure the capsule becomes
    // (cyrt::failure_guards over outside_failures).
    std::vector<Set *> failure_guards() const;

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
    // Splits the queue on a choice that escapes the set function (rule SF.1
    // of the dissertation; see allValues_step in currylib/setfunctions.cpp).
    // A configuration that made choice ``cid`` LEFT stays, and one that made
    // it RIGHT moves to ``rhs``.  One that has not made it is in both
    // queues.  Both queues record the choice (decisions), so that a
    // configuration forks on it instead of escaping it again.  Whether a
    // configuration made the choice is read from its own fingerprint, never
    // from an enclosing configuration: the capsule may be shared by
    // configurations that decided the choice differently (issue #61), and
    // each of them prunes the choice node the escape makes.  ``rhs`` must
    // be empty.
    void split(xid_type cid, Queue & rhs);
    // Clones the queue for a configuration whose binding its nested
    // evaluation read (RuntimeState::diverge; see allValues_step in
    // currylib/setfunctions.cpp).  ``copy`` must be empty.  After the call
    // both queues hold every configuration, the decisions and the absorbed
    // bindings, and ``copy`` absorbs ``binding`` for ``vid`` as well.  A
    // shared configuration is cloned before a queue steps it
    // (unshare_front), so the two queues then evolve apart.
    void clone(Queue & copy, xid_type vid, Node * binding);

  private:
    queue_type items;
    // The number of configurations in ``items``.
    size_t count = 0;
    Configuration * clone_front();
    static void let_go(Configuration *);
  };
}
