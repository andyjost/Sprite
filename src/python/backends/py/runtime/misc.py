from __future__ import absolute_import

__all__ = [
    'RuntimeFlowException'
  , 'E_CONTINUE', 'E_RESIDUAL', 'E_STEPLIMIT', 'E_TERMINATE'
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

class E_TERMINATE(RuntimeFlowException):
  '''Raised to terminate evaluation.'''

