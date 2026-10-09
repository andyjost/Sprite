#include "cyrt/builtins.hpp"
#include "cyrt/state/rts.hpp"
#include <algorithm>

namespace cyrt
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

  // Tells whether a failure met by a step of C fails the set function: the
  // flag setfunction_failures is 'escape', the evaluation is inside a set
  // function, and the path from the root of C to the failure crosses a set
  // guard, in the levels of the scan (from the root to the redex) or in the
  // guards of ``inductive`` (from the redex to the position; null when the
  // failure is at the cursor of the scan).  Such a failure is boxed: it
  // came through the box of an argument of a set function, this one or an
  // enclosing one, as the box rule of the dissertation (chapter 4) keeps
  // every reference to a boxed expression boxed.  So it is a failure of the
  // context, not of the function, and the semantics of weakly encapsulated
  // search gives the set function no value.  An unboxed failure is the
  // function's own and drops its alternative (rule SF.5), as every failure
  // does under 'encapsulate'.  The Python backend has the same test
  // (boxed_failure in rts_setfunctions.py).
  bool RuntimeState::failure_escapes(
      Configuration * C, Variable const * inductive
    )
  {
    if(this->setfunction_failures != SETF_FAILURES_ESCAPE
        || !this->in_recursive_call())
      return false;
    if(inductive && !inductive->guards.empty())
      return true;
    for(auto const & level: C->scan.frames())
      if(is_guard_level(level.cur))
        return true;
    return false;
  }

  // Fails the set function whose queue is current (see failure_escapes).
  // Records the sets of the guards the failure crossed, less the current
  // set, and returns E_SETFAIL, which every enclosing step hands out as it
  // hands E_UNWIND out, up to the nested procD, which yields it to
  // allValues_step.  That step makes the set function a failure under the
  // guards recorded: an enclosing set function whose argument the failure
  // came from fails in turn when it demands it, and a failure from no
  // enclosing argument drops the alternative of the enclosing function.
  // The step that met the failure is left as it was, with its queue: the
  // set function is gone, and nothing runs the queue again.
  tag_type RuntimeState::fail_capsule(
      Configuration * C, Variable const * inductive
    )
  {
    assert(this->in_recursive_call());
    Set * const current = this->S();
    auto & keep = this->capsule_failure_guards;
    keep.clear();
    auto record = [&](Set * set)
    {
      if(set && set != current
          && std::find(keep.begin(), keep.end(), set) == keep.end())
        keep.push_back(set);
    };
    for(auto const & level: C->scan.frames())
      if(is_guard_level(level.cur))
        record(NodeU{*level.cur}.setgrd->set);
    if(inductive)
      for(Set * set: inductive->guards)
        record(set);
    return E_SETFAIL;
  }
}
