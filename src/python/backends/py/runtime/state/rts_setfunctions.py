'''
Implements RuntimeState methods related to set functions.  This module is not
intended to be imported except by state.py.
'''

__all__ = [
    'create_setfunction', 'choice_escapes', 'guard_args', 'guard'
  , 'in_recursive_call', 'pop_queue', 'push_queue', 'qid', 'queue_scope'
  , 'SetFunctionEval', 'sid', 'update_escape_set', 'update_scape_sets'
  , 'walk_qstack'
  ]

from .. import graph
from . import queue
import contextlib

class SetFunctionEval(object):
  '''
  An object representing the evaluation of a set function.

  Created when a set-function-wrapped function is evaluated.

  Each distinct fingerprint that evaluates this object uses a separate queue.
  The queues hold *references* to Configuration objects, so steps applied in
  one queue take effect in all.  With separate queues, every outer context can
  control which values appear in its view of the set.
  '''
  def __init__(self):
    self.escape_set = set()

def create_setfunction(rts):
  sid = next(rts.setfactory)
  rts.sftable[sid] = SetFunctionEval()
  return sid

def choice_escapes(rts, cid):
  '''
  Tells whether a choice at the root of an expression should escape to an outer
  set function.  This occurs when the choice is in the escape set, and does not
  appear in the global fingerprint.
  '''
  if (rts.S is not None and cid in rts.S.escape_set) or rts.C.escape_all:
    return not any(cid in config.fingerprint for config in walk_qstack(rts))
  return False

def guard_args(rts, expr, guards):
  guards = iter(guards)
  last_sid = next(guards)
  for sid in guards:
    expr = graph.Node(rts.setfunctions._SetGuard, sid, expr)
  yield rts.setfunctions._SetGuard
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

  Parameters:
  -----------
    ``firstconfig``
      The optional first (i.e., current) configuration.  If provided , it will
      take the place of the current configuration.  This does not affect any
      parent configuration in the chain.
  '''
  firstconfig = rts.C if firstconfig is None else firstconfig
  yield firstconfig
  for qid in rts.qstack[-2::-1]:
    yield rts.qtable[qid][0]

