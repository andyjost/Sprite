'''
Implements RuntimeState methods related to set functions.  This module is not
intended to be imported except by rts.py.
'''

__all__ = [
    'create_queue', 'create_setfunction', 'choice_escapes', 'guard_args'
  , 'guard', 'in_recursive_call', 'owns_decision', 'pop_queue', 'push_queue'
  , 'qid', 'queue_scope', 'SetFunctionEval', 'sid', 'split_queue'
  , 'update_escape_set', 'update_scape_sets', 'walk_qstack'
  ]

from ....common import LEFT, RIGHT, UNDETERMINED
from copy import copy
from .. import graph
from . import queue
import contextlib

class SetFunctionEval(object):
  '''
  An object representing the evaluation of a set function.

  Created when a set-function-wrapped function is evaluated.  It holds the
  escape set: the choices that escape the set function.  The queues of the
  set function name it by its id (Queue.sid); a choice that escapes splits
  a queue into two (split_queue), one per side of the choice.  The queues
  hold *references* to Configuration objects, so steps applied in one queue
  take effect in all.  A step therefore never writes the side of a choice
  that an enclosing configuration decided into a configuration or into the
  shared graph: the side is read at a fork through the queue stack
  (read_fp), after the escape of the choice has bound the queue to that
  side (choice_escapes, owns_decision).
  '''
  def __init__(self):
    self.escape_set = set()

def create_queue(rts, sid, goal):
  with rts.queue_scope(sid=sid, trace=False):
    rts.set_goal(goal)
    return rts.qid

def create_setfunction(rts):
  sid = next(rts.setfactory)
  rts.sftable[sid] = SetFunctionEval()
  return sid

def choice_escapes(rts, cid):
  '''
  Tells whether the choice at the root of the current configuration escapes
  the set function: rule SF.1 of the dissertation (chapter 4, Figure 4.2).
  The choice escapes when it is in the escape set of the set of the current
  queue, or of an enclosing set, and the queue has not escaped it before.
  A choice in the escape set of an enclosing set came through the guard of
  an argument of that set function, so it is non-determinism from outside
  that capsule, and from outside every capsule nested in it.  An escape
  splits the queue, and both queues record the choice (split_queue), so a
  configuration meets it a second time without an escape: it forks on it,
  and the fork reads the side from its own fingerprint, or from the
  enclosing configuration, which runs this queue because it decided the
  choice that way.  A configuration that decided the choice itself, through
  an occurrence outside the guards (set f $< x $> x), still escapes it, and
  the split sorts it to its side; a refusal would keep the two sides of the
  argument in one set.  A capsule consumed in part may be shared by
  enclosing configurations that decided the choice differently (issue
  #61): the choice node the escape makes is pruned by each of them, where
  a refusal would write the values of one into the graph the other reads.

  A choice in no escape set escapes as well when an enclosing configuration
  has decided it: a captured occurrence (set1 (constT x) 0) of a choice
  that the outside decided after the capsule started.  A fork would prune
  it, inside a capsule that another enclosing configuration, with the other
  side, may share, to the side of the configuration that runs the capsule
  now.  The escape splits the capsule instead, and each side prunes its own
  copy.  A choice that no enclosing configuration decided is encapsulated:
  the configuration forks on it.  The fingerprint of the configuration
  itself is not read here.  The C++ runtime has the same rule
  (RuntimeState::choice_escapes).
  '''
  if not rts.in_recursive_call:
    return False
  escapes = rts.C.escape_all or any(
      cid in rts.sftable[sid].escape_set
          for sid in (rts.qtable[qid].sid for qid in reversed(rts.qstack))
          if sid is not None
    )
  if not escapes:
    gid = rts.grp_id(cid)
    enclosing = rts.walk_qstack()
    next(enclosing)
    escapes = any(gid in config.fingerprint for config in enclosing)
  return escapes and cid not in rts.Q.decisions

def owns_decision(rts, cid):
  '''
  Tells whether the current configuration owns the decision of choice
  ``cid``: it made the choice itself, or its queue was split on the choice
  (Queue.decisions), so every configuration that runs the queue decided the
  choice the same way.  A configuration that owns the decision may take the
  side of an escaped choice at once (allValues in currylib/setfunctions.py).
  One that reads the side from an enclosing configuration alone may be in a
  capsule that enclosing configurations with different decisions share, so
  the side goes into no state of its own: the choice node stays, reaches
  its root, and escapes in turn (choice_escapes), up to the configuration
  that decided it.  The C++ runtime has the same test
  (RuntimeState::owns_decision).
  '''
  return rts.grp_id(cid) in rts.C.fingerprint or cid in rts.Q.decisions

def split_queue(rts, qid, cid):
  '''
  Splits queue ``qid`` on choice ``cid``, which escapes the set function, and
  returns the id of the new queue (rule SF.1; see allValues in
  currylib/setfunctions.py).  A configuration that made the choice LEFT
  stays, and one that made it RIGHT moves to the new queue.  One that has
  not made it is in both queues.  Both queues record the choice
  (Queue.decisions), so that a configuration forks on it instead of
  escaping it again (choice_escapes).  Whether a configuration made the
  choice is read from its own fingerprint, never from an enclosing
  configuration.  The C++ runtime has the same split (Queue::split).
  '''
  Q = rts.qtable[qid]
  rhs_qid = next(rts.setfactory)
  rhs = rts.qtable[rhs_qid] = copy(Q)
  for queue_, lr in ((Q, LEFT), (rhs, RIGHT)):
    kept = [
        config for config in queue_
            if config.fingerprint.get(
                rts.grp_id(cid, config=config), UNDETERMINED
              ) in (lr, UNDETERMINED)
      ]
    queue_.clear()
    queue_.extend(kept)
    queue_.decisions.add(cid)
  return rhs_qid

def guard_args(rts, expr, guards):
  guards = iter(guards)
  last_sid = next(guards)
  for sid in guards:
    expr = graph.Node(rts.SetGuard, sid, expr)
  yield rts.SetGuard
  yield last_sid
  yield expr

def guard(rts, expr, guards, target=None):
  if not guards:
    return expr
  else:
    return graph.Node(*guard_args(rts, expr, guards), target=target)

def in_recursive_call(rts):
  return len(rts.qstack) > 1

def pop_queue(rts, trace=True):
  rts.qstack.pop()
  if trace:
    rts.trace.activate_queue(rts.qstack[-1])

def push_queue(rts, sid=None, qid=None, trace=True):
  if qid is None:
    qid = next(rts.setfactory)
    rts.qtable[qid] = queue.Queue([], sid=sid)
  if trace:
    rts.trace.activate_queue(qid)
  rts.qstack.append(qid)

def qid(rts):
  '''The ID of the current queue.'''
  return rts.qstack[-1]

@contextlib.contextmanager
def queue_scope(rts, sid=None, qid=None, trace=True):
  rts.push_queue(sid, qid, trace=trace)
  try:
    yield
  finally:
    rts.pop_queue(trace=trace)

def sid(rts):
  '''The ID of the current set.'''
  return rts.Q.sid

def update_escape_set(rts, sid, cid):
  setf = rts.sftable[sid]
  setf.escape_set.add(cid)

def update_escape_sets(rts, sids, cid):
  for sid in sids:
    if sid is not None:
      rts.update_escape_set(sid=sid, cid=cid)

def walk_qstack(rts, firstconfig=None):
  '''
  Walk the chain of active configurations up the queue stack.  This visits each
  set function application up to the top.

  Args:
    firstconfig:
      The optional first (i.e., current) configuration.  If provided , it will
      take the place of the current configuration.  This does not affect any
      parent configuration in the chain.

  Yields:
    Each active configuration on the stack.
  '''
  firstconfig = rts.C if firstconfig is None else firstconfig
  yield firstconfig
  for qid in rts.qstack[-2::-1]:
    yield rts.qtable[qid][0]

