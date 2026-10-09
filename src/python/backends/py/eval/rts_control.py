'''
Implements RuntimeState methods that manipulate the work queue.  This module is
not intended to be imported except by rts.py.
'''

from ....common import T_FUNC
from ...generic.eval.control import (
    E_RESIDUAL, E_RESTART, E_STEPLIMIT, E_TERMINATE, E_UNWIND
  )
from ..graph.copy import GraphCopier, Skipper
from .... import exceptions, inspect
from .. import graph

__all__ = [
    'append', 'catch_control', 'count_step', 'drop', 'extend', 'is_io'
  , 'make_value', 'overflow', 'raise_deferred_error', 'ready'
  , 'release_value', 'restart', 'rotate', 'suspend', 'unwind'
  ]

def append(rts, config):
  '''Append a configuration to the queue.'''
  rts.Q.append(config)

def catch_control(
    rts, ground=True, nondet=False, residual=False, restart=False
  , steplimit=False, unwind=False
  ):
  '''
  Catch and handle flow-control exceptions.

  Args:
    ground:
      Require ground terms.  Propagate E_RESIDUAL only if this is true.

    nondet:
      Catch non-determinism and raise NondetMonadError if it occurs.  This takes
      priority over all other options.

    residual:
      Handle residuals by updating the current configuration and rotating the
      queue.

    restart:
      Catch and ignore E_RESTART.

    steplimit:
      Handle a spent step budget by rotating the queue.  The exception names
      the queue to rotate (see count_step).  When that is an enclosing queue,
      the exception propagates to the handler of that queue.  The
      set-function evaluations in between are suspended.  They resume when
      their configuration runs again.  A RecursionError raised by deep
      evaluation goes to ``overflow``: the configuration runs again after the
      others when it made progress, and an alternative that is stuck at the
      same depth is dropped.  So the other alternatives still produce their
      values.

    unwind:
      Catch and ignore E_UNWIND.

  Returns:
    A context manager.
  '''
  return ControlHandler(
      rts, ground, nondet, residual, restart, steplimit, unwind
    )

class ControlHandler(object):
  '''
  The context manager returned by ``catch_control``.  It is a plain class, not
  a generator, because the evaluator enters one per rewrite step.
  '''
  __slots__ = (
      'rts', 'ground', 'nondet', 'residual', 'restart', 'steplimit', 'unwind'
    )

  def __init__(self, rts, ground, nondet, residual, restart, steplimit, unwind):
    self.rts = rts
    self.ground = ground
    self.nondet = nondet
    self.residual = residual
    self.restart = restart
    self.steplimit = steplimit
    self.unwind = unwind

  def __enter__(self):
    return None

  def __exit__(self, exc_type, exc, tb):
    # A true result swallows the exception.  See catch_control.
    if exc_type is None:
      return False
    if issubclass(exc_type, E_UNWIND):
      if self.nondet:
        raise exceptions.NondetMonadError()
      return bool(self.unwind)
    if issubclass(exc_type, E_RESIDUAL):
      if self.nondet:
        raise exceptions.NondetMonadError()
      if self.residual:
        self.rts.C.residuals.update(exc.ids)
        self.rts.rotate()
        return True
      return not self.ground
    if issubclass(exc_type, E_RESTART):
      return bool(self.restart)
    if issubclass(exc_type, E_STEPLIMIT):
      if not self.steplimit or (exc.qid is not None and exc.qid != self.rts.qid):
        return False
      self.rts.rotate()
      return True
    if issubclass(exc_type, RecursionError):
      return bool(self.steplimit) and bool(self.rts.overflow(exc))
    return False

def overflow(rts, error):
  '''
  Handle a RecursionError raised by the evaluation of the current
  configuration.  Returns True when D continues with the current queue, and
  False when the error goes to the enclosing queue.  This mirrors
  ``RuntimeState::unwind`` of the C++ backend.

  A configuration that took no step since it last overflowed is stuck: it
  repeats the same descent and overflows at the same point.  The steps of a
  nested set-function evaluation count for the enclosing configuration.
  Re-scanning a configuration from its root repeats the descent but loses no
  work, because the graph holds every result.

  In the outermost queue, a configuration that made progress runs again after
  the others.  A stuck one is dropped.  Its error waits in
  ``rts.deferred_error`` until the queue is empty (see D and ready), so the
  other alternatives still produce their values.  In a nested queue, a
  configuration cannot be dropped without losing a value of the set function.
  It runs again after the others when any step was taken since it last
  overflowed.  When no step was taken, the enclosing queue decides.
  '''
  C = rts.C
  if rts.in_recursive_call:
    steps_total = rts.stepcounter.global_count
    if len(rts.Q) > 1 and C.overflow_total != steps_total:
      C.overflow_total = steps_total
      rts.rotate()
      return True
    return False
  if C.overflow_at != C.steps:
    C.overflow_at = C.steps
    rts.rotate()
    return True
  if rts.deferred_error is None:
    rts.deferred_error = error
  rts.drop()
  return True

def raise_deferred_error(rts):
  '''
  Raise the error of an alternative dropped at the stack limit, if there is
  one.  Only the outermost queue reports it, after the other alternatives
  have run.  See overflow.
  '''
  if not rts.in_recursive_call and rts.deferred_error is not None:
    error, rts.deferred_error = rts.deferred_error, None
    raise error

def count_step(rts):
  '''
  Account for one rewrite step of the current configuration.

  Called from S after each completed step.  The step belongs to the current
  configuration and to the configuration at the head of each enclosing queue,
  because a set-function evaluation runs inside a step of the enclosing
  configuration.  Each of them counts the step and spends one unit of its
  budget.

  When a configuration has spent its budget, the queue that holds it rotates
  so that the other configurations get a turn.  A queue with one configuration
  cannot rotate.  The outermost queue that can rotate is the target.  D
  rotates it when it handles E_STEPLIMIT, which carries the ID of the queue
  (see catch_control).  The exception suspends the nested evaluations.  They
  resume when their configuration runs again.  A nested queue that can rotate
  is rotated here, in place, before the exception is raised.  Otherwise a
  nested queue whose budget expires together with the budget of an enclosing
  queue would never rotate.  With no step budget, only the counts are kept.
  '''
  budget = rts.step_budget
  expired = [] # the queues to rotate, innermost first
  for qid in reversed(rts.qstack):
    Q = rts.qtable[qid]
    C = Q[0]
    C.steps += 1
    if budget is None:
      continue
    C.budget_used += 1
    if C.budget_used >= budget:
      C.budget_used = 0
      if len(Q) > 1:
        expired.append(qid)
  if expired:
    target = expired.pop()
    for qid in expired:
      rts.qtable[qid].rotate(-1)
    raise E_STEPLIMIT(target)

def drop(rts, trace=True):
  '''Drop the current configuration.'''
  rts.Q.popleft()
  if trace:
    rts.trace.failed()

def extend(rts, configs):
  '''Extend the queue.'''
  rts.Q.extend(configs)

# The names of the functions that perform I/O.  See is_io.
IO_FUNCTION_NAMES = frozenset([
    'prim_putChar', 'prim_readFile', 'prim_writeFile', 'prim_appendFile'
  , 'appendFile', 'putStr', 'putChr', 'putStrLn', 'print', 'seqIO'
  , 'returnIO', 'bindIO', 'getChar'
  ])

def is_io(rts, func):
  assert func.info.tag == T_FUNC
  return func.info.name in IO_FUNCTION_NAMES

def make_value(rts, arg=None, config=None):
  config = config or rts.C
  arg = config.root if arg is None else arg
  if inspect.isa(arg, rts.prelude.IO):
    return arg.successors[0]
  skipgrds = set([] if rts.sid is None else [rts.sid])
  copier = GraphCopier(skipper=Skipper(skipfwd=True, skipgrds=skipgrds))
  value = copier(arg)
  # The copies of the free variables of the value live outside this
  # evaluation.  Count them, so that a later goal that holds the value is
  # walked.  See InterpreterState.external_freevars.
  rts.istate.external_freevars += copier.freevars
  return value

def ready(rts):
  '''
  Checks whether the runtime is ready to continue evaluation.  Skips over
  blocked configurations and raises EvaluationSuspended if the queue contains
  only blocked configurations.  Returns True when the queue is not empty and
  the configuration at the head is ready to be further evaluated.
  '''
  Q = rts.Q
  if Q:
    if not Q[0].residuals:
      # The configuration at the head is ready.  This is the common case.
      return True
    try:
      i = next(i for i, c in enumerate(Q) if _make_ready(rts, c))
    except StopIteration:
      # Every configuration is blocked.  The error of a dropped alternative
      # comes first.
      rts.raise_deferred_error()
      raise exceptions.EvaluationSuspended()
    else:
      rts.rotate(i)
      return True

def _make_ready(rts, config):
  '''
  Attempt to make ready the specified configuration.  A configuration is ready
  if it has no residuals, or if there exists some residual with a binding or
  generator in that configuration.
  '''
  n = len(config.residuals)
  if n:
    # The information is read from this configuration, not from the head of
    # the queue: a binding is private to the configuration that made it.  A
    # test against the head released a configuration behind it on the
    # strength of the head's binding, and the released step suspended again
    # at once, without end.  The C++ runtime passes the configuration too
    # (_make_ready in rts_control.cpp).
    config.residuals = set(
        vid for vid in config.residuals
            if rts.is_void(rts.vtable[vid], config)
      )
    return len(config.residuals) < n
  else:
    return True

def release_value(rts):
  '''
  Makes a value from the first configuration, detaches that configuration
  from the computation state, and then returns the value.
  '''
  rts.telemetry._values += 1
  if rts.checker is not None:
    rts.checker.yield_(rts.C)
  value = rts.make_value()
  rts.drop(trace=False)
  return value

def restart(rts):
  '''Unwind to the next N() or S() procedure.'''
  raise E_RESTART()

def rotate(rts, n=1):
  '''
  Rotate the queue by ``n`` positions.  By default, the current configuration
  is moved to the end.
  '''
  rts.Q.rotate(-n)

def suspend(rts, arg, config=None):
  '''Suspend a configuration with the given residual(s).'''
  if isinstance(arg, (list, tuple)):
    ids = set(
        [rts.obj_id(x, config) for x in arg]
      + [rts.grp_id(x, config) for x in arg]
      )
  else:
    ids = set([rts.obj_id(arg, config), rts.grp_id(arg, config)])
  assert ids
  raise E_RESIDUAL(list(ids))

def unwind(rts):
  '''Unwind to the next N() or S() procedure.'''
  raise E_UNWIND()

