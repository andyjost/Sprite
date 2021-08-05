'''
Implements RuntimeState methods that manipulate the work queue.  This module is
not intended to be imported except by state.py.
'''

from .....exceptions import EvaluationSuspended
from ..control import E_RESIDUAL, E_RESTART
from . import integer

__all__ = ['append', 'drop', 'extend', 'ready', 'rotate']

def append(self, config):
  '''Append a configuration to the queue.'''
  self.queue.append(config)

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
  for vid in config.residuals:
    x = self.vtable[vid]
    if self.has_generator(x) or self.has_binding(x): # or integer.narrowed_int_value(self, x, config) is not None:
      config.residuals = set()
      break
  return not config.residuals

def rotate(self, n=1):
  '''
  Rotate the queue by ``n`` positions.  By default, the current configuration
  is moved to the end.
  '''
  self.queue.rotate(-n)

