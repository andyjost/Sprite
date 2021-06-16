from .fairscheme import *
from .graph import *
from .misc import *
from .... import context
import itertools

__all__ = [
    'Runtime'

  # From fairscheme.
  , 'Evaluator'
  , 'Frame'
  , 'freshvar'
  , 'freshvar_args'
  , 'get_generator'
  , 'get_id'
  , 'has_generator'
  , 'hnf'
  , 'LEFT', 'RIGHT', 'UNDETERMINED'
  , 'RuntimeState'
  , 'InterpreterState'
  , 'StepCounter'

  # From graph.
  , 'InfoTable'
  , 'Node'
  , 'Replacer'
  , 'replace'
  , 'replace_copy'
  , 'rewrite'

  # From misc.
  , 'RuntimeFlowException'
  , 'E_CONTINUE', 'E_RESIDUAL', 'E_STEPLIMIT'
  ]


class Runtime(context.Runtime):
  '''Implementation of the abstract runtime system for the Python backend.'''
  @property
  def Node(self):
    return Node

  @property
  def InfoTable(self):
    return InfoTable

  def init_interpreter_state(self, interp):
    interp._its = InterpreterState(interp)

  def get_interpreter_state(self, interp):
    return interp._its

  @property
  def prelude(self):
    from . import prelude
    return prelude

  @property
  def evaluate(self):
    return lambda *args, **kwds: Evaluator(*args, **kwds).evaluate()

  @property
  def get_id(self):
    return get_id
