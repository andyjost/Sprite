'''
Implements RuntimeState methods that manipulate the work queue.  This module is
not intended to be imported except by state.py.
'''

from ..control import E_CONTINUE, E_RESIDUAL, E_RESTART
from .....exceptions import EvaluationSuspended
from . import integer
import contextlib

__all__ = [
    'append', 'catch_control', 'drop', 'extend', 'ready', 'restart', 'rotate'
  , 'suspend', 'unwind'
  ]

def append(self, config):
  '''Append a configuration to the queue.'''
  self.queue.append(config)

@contextlib.contextmanager
def catch_control(
    self, ground=True, residual=False, restart=False, unwind=False
  ):
  '''Catch and handle flow-control exceptions.'''
  try:
    yield
  except E_CONTINUE:
    if not unwind:
      raise
  except E_RESIDUAL as res:
    if residual:
      rts.C.residuals.update(res.ids)
      rts.rotate()
    elif ground:
      raise
  except E_RESTART:
    if not restart:
      raise

def drop(self):
  '''Drop the current configuration.'''
  self.queue.popleft()

def extend(self, configs):
  '''Extend the queue.'''
  self.queue.extend(configs)

def ready(self):
  '''
  Checks whether the runtime is ready to continue evaluation.  Skips over
  blocked configurations and raises EvaluationSuspended if the queue contains
  only blocked configurations.  Returns True when the queue is not empty and
  the configuration at the head is ready to be further evaluated.
  '''
  if self.queue:
    try:
      i = next(i for i, c in enumerate(self.queue) if _make_ready(self, c))
    except StopIteration:
      raise EvaluationSuspended()
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
  self.queue.rotate(-n)

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
  raise E_CONTINUE()

