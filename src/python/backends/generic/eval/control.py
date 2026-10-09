'''Defines flow-control exceptions.'''

__all__ = [
    'RuntimeFlowException'
  , 'E_DIVERGE', 'E_RESIDUAL', 'E_SETFAIL', 'E_STEPLIMIT', 'E_TERMINATE'
  , 'E_UNWIND'
  ]

class RuntimeFlowException(BaseException):
  '''
  The base class for exceptions used by the runtime system for flow control.
  These should always be caught and handled.
  '''
  pass

class E_UNWIND(RuntimeFlowException):
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
    Args:
      ``ids``
          A collection of free variable IDs (ints) blocking evaluation.
    '''
    assert all(isinstance(x, int) for x in ids)
    self.ids = set(ids)


class E_STEPLIMIT(RuntimeFlowException):
  '''
  Raised when a configuration has spent its step budget.  ``qid`` is the ID of
  the queue to rotate.  None means the queue of the first handler.
  '''
  def __init__(self, qid=None):
    self.qid = qid

class E_SETFAIL(RuntimeFlowException):
  '''
  Raised when a boxed failure is demanded inside a set function under the
  flag setfunction_failures (see boxed_failure in rts_setfunctions.py of the
  Python backend).  ``sids`` are the ids of the enclosing sets whose guards
  the failure crossed: the set function becomes a failure under their
  guards (see allValues in currylib/setfunctions.py).
  '''
  def __init__(self, sids):
    self.sids = list(sids)

class E_DIVERGE(RuntimeFlowException):
  '''
  Raised when the nested evaluation of a set function reads a binding of an
  enclosing configuration (get_binding in rts_bindings.py of the Python
  backend): the capsule depends on the private state of that configuration,
  which another configuration with another binding may share (issue #86).
  allValues (currylib/setfunctions.py) clones the capsule for that
  configuration.  ``qid`` is the queue to clone, ``vid`` the id under which
  its configurations looked the variable up, and ``binding`` the binding
  the clone absorbs.
  '''
  def __init__(self, qid, vid, binding):
    self.qid = qid
    self.vid = vid
    self.binding = binding

class E_TERMINATE(RuntimeFlowException):
  '''Raised to terminate evaluation.'''

class E_RESTART(RuntimeFlowException):
  '''
  Raised to indicate evaluation of a configuration must restart.
  '''
