'''
Implements RuntimeState methods that manipulate the work queue.  This module is
not intended to be imported except by state.py.
'''

from .....common import T_FUNC
from ..control import E_RESIDUAL, E_RESTART, E_TERMINATE, E_UNWIND
from ..graph.copy import copygraph
from ..... import exceptions
from .. import graph
from ..... import inspect
import contextlib

__all__ = [
    'append', 'catch_control', 'drop', 'extend', 'is_io', 'make_value', 'ready'
  , 'release_value', 'restart', 'rotate', 'suspend', 'unwind'
  ]

def append(rts, config):
  '''Append a configuration to the queue.'''
  rts.Q.append(config)

@contextlib.contextmanager
def catch_control(
    rts, ground=True, nondet=False, residual=False, restart=False, unwind=False
  ):
  '''
  Catch and handle flow-control exceptions.

  Parameters:
  -----------
    ``ground``
      Require ground terms.  Propagate E_RESIDUAL only if this is true.

    ``nondet``
      Catch non-determinism and raise NondetMonadError if it occurs.  This takes
      priority over all other options.

    ``residual``
      Handle residuals by updating the current configuration and rotating the
      queue.

    ``restart``
      Catch and ignore E_RESTART.

    ``unwind``
      Catch and ignore E_UNWIND.
  '''
  try:
    yield
  except E_UNWIND:
    if nondet:
      raise exceptions.NondetMonadError()
    elif not unwind:
      raise
  except E_RESIDUAL as res:
    if nondet:
      raise exceptions.NondetMonadError()
    elif residual:
      rts.C.residuals.update(res.ids)
      rts.rotate()
    elif ground:
      raise
  except E_RESTART:
    if not restart:
      raise

def drop(rts, trace=True):
  '''Drop the current configuration.'''
  rts.Q.popleft()
  if trace:
    rts.trace.failed()

def extend(rts, configs):
  '''Extend the queue.'''
  rts.Q.extend(configs)

def is_io(rts, func):
  assert func.info.tag == T_FUNC
  return func.info.name in [
      'prim_putChar', 'prim_readFile', 'prim_writeFile', 'appendFile'
    , 'putStr', 'putChr', 'putStrLn', 'print', 'seqIO'
    , 'returnIO', 'bindIO', 'getChar'
    ]

def make_value(rts, arg=None, config=None):
  config = config or rts.C
  arg = config.root if arg is None else arg
  if inspect.isa(arg, rts.prelude.IO):
    return arg.successors[0]
  skipgrds = set([] if rts.sid is None else [rts.sid])
  return copygraph(arg, skipfwd=True, skipgrds=skipgrds)

def ready(rts):
  '''
  Checks whether the runtime is ready to continue evaluation.  Skips over
  blocked configurations and raises EvaluationSuspended if the queue contains
  only blocked configurations.  Returns True when the queue is not empty and
  the configuration at the head is ready to be further evaluated.
  '''
  if rts.Q:
    try:
      i = next(i for i, c in enumerate(rts.Q) if _make_ready(rts, c))
    except StopIteration:
      raise exceptions.EvaluationSuspended()
    else:
      rts.rotate(i)
      return True

def _make_ready(rts, config):
  '''
  Attempt to make ready the specified configuration.  A configuration is ready
  if it has no residuals, or if there exists some residual with a binding or
  generator.
  '''
  n = len(config.residuals)
  if n:
    config.residuals = set(
        vid for vid in config.residuals if rts.is_void(rts.vtable[vid])
      )
    return len(config.residuals) < n
  else:
    return True
  return not n or len(config.residuals) < n

def release_value(rts):
  '''
  Makes a value from the first configuration, detaches that configuration
  from the computation state, and then returns the value.
  '''
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

