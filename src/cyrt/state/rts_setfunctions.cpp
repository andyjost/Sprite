#include "cyrt/state/rts.hpp"

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
  // configuration has decided it: a captured occurrence (set1 (constT x) 0)
  // of a choice that the outside decided after the capsule started.  A fork
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
}
