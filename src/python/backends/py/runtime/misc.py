from __future__ import absolute_import

__all__ = [
    'get_stepper'
  , 'StepCounter'
  , 'RuntimeFlowException'
  , 'E_CONTINUE', 'E_RESIDUAL', 'E_STEPLIMIT', 'E_UPDATE_CONTEXT'
  ]

class RuntimeFlowException(BaseException):
  '''
  The base class for exceptions used by the runtime system for flow control.
  These should always be caught and handled.
  '''
  pass

class E_CONTINUE(RuntimeFlowException):
  '''
  Raised when control must break out of the recursive match-eval loop.  This
  occurs when a symbol requiring exceptional handing (e.g., FAIL or CHOICE) was
  placed in a needed position, or when a variable is replaced by a value by
  rewriting the root node.
  '''
  # For example, when reducing g (f (a ? b)), a pull-tab step will replace f
  # with a choice.  Afterwards, this exception is raised to return control to
  # g.


class E_RESIDUAL(RuntimeFlowException):
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


class E_STEPLIMIT(RuntimeFlowException):
  '''Raised when the step limit is reached.'''


class E_UPDATE_CONTEXT(RuntimeFlowException):
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

