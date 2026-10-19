#include "curryrt/builtins.hpp"
#include "curryrt/checker.hpp"
#include "curryrt/state/rts.hpp"
#include <algorithm>

namespace curryrt
{
  void RuntimeState::push_queue(Queue * queue, TraceOpt trace)
  {
    assert(queue);
    this->qstack.push_back(queue);
    #ifdef SPRITE_TRACE_ENABLED
    if(trace && this->trace)
      this->trace->activate_queue(queue);
    #endif
  }

  void RuntimeState::pop_queue(TraceOpt trace)
  {
    this->qstack.pop_back();
    assert(!this->qstack.empty());
    #ifdef SPRITE_TRACE_ENABLED
    if(trace && this->trace)
      this->trace->activate_queue(this->Q());
    #endif
  }

  // Tells whether the choice at the root of C, the front of the current
  // queue, escapes the set function: rule SF.1 of the dissertation (chapter
  // 4, Figure 4.2).  The choice escapes when it is in the escape set of the
  // set of this queue, or of an enclosing set, and the queue has not
  // escaped it before.  A choice in the escape set of an enclosing set came
  // through the guard of an argument of that set function, so it is
  // non-determinism from outside that capsule, and from outside every
  // capsule nested in it.  An escape splits the queue, and both queues
  // record the choice (Queue::split), so a configuration meets it a second
  // time without an escape: it forks on it, and the fork reads the side
  // from its own fingerprint, or from the enclosing configuration, which
  // runs this queue because it decided the choice that way.  A
  // configuration that decided the choice itself, through an occurrence
  // outside the guards (set f $< x $> x), still escapes it, and the split
  // sorts it to its side; a refusal would keep the two sides of the
  // argument in one set.  A capsule consumed in part may be shared by
  // enclosing configurations that decided the choice differently (issue
  // #61): the choice node the escape makes is pruned by each of them,
  // where a refusal would write the values of one into the graph the other
  // reads.
  //
  // A choice in no escape set escapes as well when an enclosing
  // configuration has decided it: a captured occurrence (set f $< x, or an
  // encapsulated expression) of a choice that the outside decided after
  // the capsule started.  A fork
  // would prune it, inside a capsule that another enclosing configuration,
  // with the other side, may share, to the side of the configuration that
  // runs the capsule now.  The escape splits the capsule instead, and each
  // side prunes its own copy.  A choice that no enclosing configuration
  // decided is encapsulated: the configuration forks on it.  The
  // fingerprint of C itself is not read here.
  bool RuntimeState::choice_escapes(Configuration * C, xid_type cid)
  {
    if(!this->in_recursive_call())
      return false;
    bool escapes = C->escape_all;
    auto const rbegin = this->qstack.rbegin(), rend = this->qstack.rend();
    for(auto p=rbegin; !escapes && p!=rend; ++p)
    {
      Set * S = (*p)->set;
      escapes = S && S->escape_set.count(cid);
    }
    if(!escapes)
    {
      xid_type const gid = C->grp_id(cid);
      for(auto p=rbegin+1; !escapes && p!=rend; ++p)
        escapes = (*p)->front()->fingerprint.test(gid) != UNDETERMINED;
    }
    return escapes && !this->Q()->decided(cid);
  }

  // Tells whether C owns the decision of choice ``cid``: it made the choice
  // itself, or its queue was split on the choice (Queue::decisions), so
  // every configuration that runs the queue decided the choice the same
  // way.  A configuration that owns the decision may take the side of an
  // escaped choice at once (allValues_step).  One that reads the side from
  // an enclosing configuration alone may be in a capsule that enclosing
  // configurations with different decisions share, so the side goes into
  // no state of its own: the choice node stays, reaches its root, and
  // escapes in turn (choice_escapes), up to the configuration that decided
  // it.
  bool RuntimeState::owns_decision(Configuration * C, xid_type cid)
  {
    return C->fingerprint.test(C->grp_id(cid)) != UNDETERMINED
        || this->Q()->decided(cid);
  }

  // A level of the scan whose node is a set guard: the path from the root of
  // the configuration to the position of the scan crosses the guard.
  static inline bool is_guard_level(Cursor const & cur)
  {
    return cur.kind == 'p' && *cur && (*cur)->info->tag == T_SETGRD;
  }

  // Records a failure met by a step of C in its capsule: rule (d1) of the
  // failure rule F2 in its deferred form (Definition 2.94 of the note on
  // the Fair Scheme).  The step that met the failure drops the
  // configuration as every failure does (procD on T_FAIL; procN and hnf
  // hand the failure up to it).  This records what the failure was for the
  // verdict on the empty queue (Queue::fails_at_end and
  // Queue::failure_guards; allValues_step in currylib/setfunctions.cpp).
  //
  // The failure is boxed when the path from the root of C to it crosses a
  // set guard, in the levels of the scan (from the root to the redex) or in
  // the guards of ``inductive`` (from the redex to the position; null when
  // the failure is at the cursor of the scan).  Such a failure came through
  // the box of an argument of a set function, this one or an enclosing one,
  // as the box rule of the dissertation (chapter 4) keeps every reference
  // to a boxed expression boxed.  So it is a failure of the context, not of
  // the function: the capsule records an outside failure with the sets of
  // the enclosing guards it crossed, less the current set, and the level at
  // which it entered the chain of the capsules.  A failure that crossed no
  // guard is the function's own: the capsule records an inside failure
  // (rule SF.5 of the dissertation drops the alternative).  A capsule
  // whose queue empties with no value, no inside failure and some outside
  // failure is itself a failure, the semantics of weakly encapsulated
  // search (Christiansen, Hanus, Reck and Seidel, PPDP 2013), as KiCS2
  // behaves.  Outside every set function nothing is recorded.
  //
  // A failure is observed at the position that met it first, with the
  // whole path, and again at each level above it on the way to the root,
  // with a shorter path (hnf forwards the redex to the failure, and the
  // caller meets the failure at the redex).  The first observation makes
  // the record and sets Configuration::failure_recorded; the rest make
  // none.  A constraint that fails at the root of procD (the occurs
  // check, or the union of two classes with different instances) is a
  // failure at the root like a failure cell there: the path crossed no
  // guard, so the record is an inside failure.  The Python backend has
  // the same rule (record_failure in rts_setfunctions.py).
  //
  // The level of an outside failure is failure_level, and the choice of
  // the records at the end of the capsule is failure_guards (queue.cpp);
  // the checker calls both (Checker::check_failure_record and
  // check_capsule_end), so a change of the reading of rule (d3) touches
  // those two functions alone.
  void RuntimeState::record_failure(
      Configuration * C, Variable const * inductive
    )
  {
    if(!this->in_recursive_call() || C->failure_recorded)
      return;
    C->failure_recorded = true;
    Queue * const Q = this->Q();
    Set * const current = Q->set;
    // The guards the path crossed, from the root down, without repetition.
    std::vector<Set *> crossed;
    auto cross = [&](Set * set)
    {
      if(set && std::find(crossed.begin(), crossed.end(), set) == crossed.end())
        crossed.push_back(set);
    };
    for(auto const & level: C->scan.frames())
      if(is_guard_level(level.cur))
        cross(NodeU{*level.cur}.setgrd->set);
    if(inductive)
      for(Set * set: inductive->guards)
        cross(set);
    if(crossed.empty())
    {
      Q->inside_failure = true;
      if(this->checker)
        this->checker->failure_recorded(C, Q, inductive, nullptr);
      return;
    }
    FailureRecord record{0, {}};
    for(Set * set: crossed)
      if(set != current)
        record.guards.push_back(set);
    record.level = this->failure_level(record.guards);
    Q->outside_failures.push_back(std::move(record));
    if(this->checker)
      this->checker->failure_recorded(
          C, Q, inductive, &Q->outside_failures.back()
        );
  }

  // The level of an outside failure that crossed the guards of ``sets``:
  // the position, innermost first, of the outermost capsule of the chain
  // among them; zero when none is on the chain (the failure crossed the
  // guard of this capsule alone).  A guard of a set that is on the chain
  // no more does not move the level.  The one place that defines the
  // level; the checker calls it.
  size_t RuntimeState::failure_level(std::vector<Set *> const & sets) const
  {
    size_t level = 0;
    size_t const n = this->qstack.size();
    for(Set * set: sets)
      for(size_t k = 1; k < n; ++k)
        if(this->qstack[n - 1 - k]->set == set)
        {
          level = std::max(level, k);
          break;
        }
    return level;
  }

  // Records a divergence: the nested evaluation read, through the queue
  // stack, the binding of ``vid`` that the configuration ``level`` levels up
  // holds (get_binding), so the capsule that configuration runs depends on
  // its private state.  Another configuration with another binding of the
  // variable may share the capsule (issue #86): the shape of
  // test_shared_capsule starts a set function over a free variable, takes
  // a value, forks, binds the variable on each side and reads the next
  // value from the same capsule.  The decision of the memo on the Fair
  // Scheme proofs (D3, route (c)): the capsule is cloned for that
  // configuration at the first divergence, which is this read.  Returns
  // E_DIVERGE, which every enclosing step hands out as it hands E_UNWIND
  // out, up to the allValues_step of that configuration (the one whose
  // nested queue is ``diverge_queue``).  That step clones the queue, which
  // absorbs the binding (Queue::clone), puts the clone into a private copy
  // of its spine and restarts; the read then finds the binding in the
  // clone (level 0).  The steps in between are left as they were, with
  // their queues, as after E_UNWIND; the configurations the clone shares
  // are cloned before a queue steps them (Queue::unshare_front).  A
  // nested capsule inside the clone diverges in turn, one level down, at
  // its next read.  The Python backend has the same step (E_DIVERGE in
  // rts_bindings.py and allValues in currylib/setfunctions.py).
  tag_type RuntimeState::diverge(size_t level, xid_type vid, Node * binding)
  {
    size_t const n = this->qstack.size();
    assert(level > 0 && level < n);
    // The queue the configuration at that level runs, and the id under
    // which its configurations looked the variable up.
    Queue * target = this->qstack[n - level];
    this->diverge_queue = target;
    this->diverge_vid = level == 1 ? vid : target->front()->grp_id(vid);
    this->diverge_binding = binding;
    return E_DIVERGE;
  }

}
