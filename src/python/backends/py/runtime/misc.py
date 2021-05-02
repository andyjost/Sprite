from __future__ import absolute_import

from .... import runtime
from .exceptions import *
from .graph import *

__all__ = [
    'freshvar'
  , 'freshvar_gen'
  , 'get_id'
  , 'get_stepper'
  , 'is_bound'
  , 'nextid'
  , 'StepCounter'
  ]

def freshvar_gen(interp):
  yield interp.prelude._Free.info
  yield interp.nextid()
  yield Node(interp.prelude.Unit.info)

def freshvar(interp):
  return Node(*freshvar_gen(interp))

def get_id(arg):
  '''Returns the choice or variable id for a choice or free variable.'''
  if isinstance(arg, Node):
    arg = arg[()]
    if arg.info.tag in [runtime.T_FREE, runtime.T_CHOICE]:
      cid = arg[0]
      assert cid >= 0
      return cid

class StepCounter(object):
  '''
  Counts the number of steps taken.  If a limit is provided, raises E_STEPLIMIT
  when the limit is reached.
  '''
  def __init__(self, limit=None):
    assert limit > 0 or limit is None
    self._limit = -1 if limit is None else limit
    self.reset()
  @property
  def count(self):
    return self._count
  @property
  def limit(self):
    return self._limit
  def increment(self):
    self._count += 1
    if self._count == self.limit:
      raise E_STEPLIMIT()
  def reset(self):
    self._count = 0


def get_stepper(interp):
  '''
  Returns a function to apply steps, according to the interp
  configuration.
  '''
  if interp.flags['trace']:
    indent = [0]
    def step(target): # pragma: no cover
      print 'S <<<' + '  ' * indent[0], str(target), getattr(interp, 'currentframe', '')
      indent[0] += 1
      try:
        target.info.step(target)
        interp.stepcounter.increment()
      finally:
        indent[0] -= 1
        print 'S >>>' + '  ' * indent[0], str(target), getattr(interp, 'currentframe', '')
  else:
    def step(target):
      target.info.step(target)
      interp.stepcounter.increment()
  return step

def is_bound(interp, freevar):
  assert freevar.info.tag == runtime.T_FREE
  return freevar[1].info is not interp.prelude.Unit.info

def nextid(interp):
  '''Generates the next available ID.'''
  return next(interp._idfactory_)

