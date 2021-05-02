from __future__ import absolute_import

from .... import runtime
from .graph import *

__all__ = [
    'freshvar'
  , 'freshvar_gen'
  , 'get_id'
  , 'get_stepper'
  , 'is_bound'
  , 'nextid'
  , 'StepCounter'
  , 'RuntimeException'
  , 'E_CONTINUE', 'E_RESIDUAL', 'E_STEPLIMIT', 'E_UPDATE_CONTEXT'
  ]

class RuntimeException(BaseException):
  pass

class E_CONTINUE(RuntimeException):
  '''
  Raised when control must break out of the recursive match-eval loop.  This
  occurs when a symbol requiring exceptional handing (e.g., FAIL or CHOICE) was
  placed in a needed position, or when a variable is replaced by a value by
  rewriting the root node.
  '''
  # For example, when reducing g (f (a ? b)), a pull-tab step will replace f
  # with a choice.  Afterwards, this exception is raised to return control to
  # g.


class E_RESIDUAL(RuntimeException):
  '''Raised when evaluation cannot complete due to uninstantiated free variables.'''
  def __init__(self, ids):
    '''
    Parameters:
    -----------
        ``ids``
            A collection of free variable IDs (ints) blocking evaluation.
    '''
    assert all(isinstance(x, int) for x in ids)
    self.ids = set(ids)


class E_STEPLIMIT(RuntimeException):
  '''Raised when the step limit is reached.'''


class E_UPDATE_CONTEXT(RuntimeException):
  '''Raised when a lazy binding requires an update to the enclosing context.'''
  def __init__(self, expr):
    '''
    Parameters:
    -----------
        ``expr``
            The replacement of the current expression in the context, after
            performing lazy binding.
    '''
    self.expr = expr

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

