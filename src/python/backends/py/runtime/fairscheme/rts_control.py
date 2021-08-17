'''
Implements RuntimeState methods that manipulate the work queue.  This module is
not intended to be imported except by state.py.
'''

from .....common import T_FUNC
from ..control import E_RESIDUAL, E_RESTART, E_TERMINATE, E_UNWIND
from ..... import exceptions
import contextlib

__all__ = [
    'append', 'catch_control', 'drop', 'extend', 'is_io', 'ready', 'restart'
  , 'rotate', 'suspend', 'unwind'
  ]

def append(self, config):
  '''Append a configuration to the queue.'''
  self.Q.append(config)

@contextlib.contextmanager
def catch_control(
    self, ground=True, nondet=False, residual=False, restart=False, unwind=False
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
      self.C.residuals.update(res.ids)
      self.rotate()
    elif ground:
      raise
  except E_RESTART:
    if not restart:
      raise

def drop(self):
  '''Drop the current configuration.'''
  self.Q.popleft()

def extend(self, configs):
  '''Extend the queue.'''
  self.Q.extend(configs)

def is_io(self, func):
  assert func.info.tag == T_FUNC
  return func.info.name in [
      'prim_putChar', 'prim_readFile', 'prim_writeFile', 'appendFile'
    , 'putStr', 'putChr', 'putStrLn', 'print', 'seqIO'
    , 'returnIO', 'bindIO', 'getChar'
    ]

def ready(self):
  '''
  Checks whether the runtime is ready to continue evaluation.  Skips over
  blocked configurations and raises EvaluationSuspended if the queue contains
  only blocked configurations.  Returns True when the queue is not empty and
  the configuration at the head is ready to be further evaluated.
  '''
  if self.Q:
    try:
      i = next(i for i, c in enumerate(self.Q) if _make_ready(self, c))
    except StopIteration:
      raise exceptions.EvaluationSuspended()
    else:
      self.rotate(i)
      return True

def _make_ready(self, config):
  '''
  Attempt to make ready the specified configuration.  A configuration is ready
  if it has no residuals, or if there exists some residual with a binding or
  generator.
  '''
  n = len(config.residuals)
  if n:
    config.residuals = set(
        vid for vid in config.residuals if self.is_free(self.vtable[vid])
      )
    return len(config.residuals) < n
  else:
    return True
  return not n or len(config.residuals) < n

def restart(self):
  '''Unwind to the next N() or S() procedure.'''
  raise E_RESTART()

def rotate(self, n=1):
  '''
  Rotate the queue by ``n`` positions.  By default, the current configuration
  is moved to the end.
  '''
  self.Q.rotate(-n)

def suspend(self, arg, config=None):
  '''Suspend a configuration with the given residual(s).'''
  if isinstance(arg, (list, tuple)):
    ids = set(
        [self.obj_id(x, config) for x in arg]
      + [self.grp_id(x, config) for x in arg]
      )
  else:
    ids = set([self.obj_id(arg, config), self.grp_id(arg, config)])
  assert ids
  raise E_RESIDUAL(list(ids))

def unwind(self):
  '''Unwind to the next N() or S() procedure.'''
  raise E_UNWIND()

