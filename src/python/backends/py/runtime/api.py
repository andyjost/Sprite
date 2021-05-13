from .fairscheme import *
from .graph import *
from .misc import *
from .... import context

__all__ = [
    'Runtime'

  # From fairscheme.
  , 'D'
  , 'Evaluator'
  , 'Frame'
  , 'freshvar'
  , 'freshvar_args'
  , 'get_generator'
  , 'get_id'
  , 'has_generator'
  , 'hnf'
  , 'LEFT'
  , 'N'
  , 'RIGHT'
  , 'S'
  , 'UNDETERMINED'

  # From graph.
  , 'InfoTable'
  , 'Node'
  , 'Replacer'
  , 'replace'
  , 'replace_copy'
  , 'rewrite'

  # From misc.
  , 'get_stepper'
  , 'StepCounter'
  , 'RuntimeFlowException'
  , 'E_CONTINUE', 'E_RESIDUAL', 'E_STEPLIMIT', 'E_UPDATE_CONTEXT'
  ]


class Runtime(context.Runtime):
  '''Implementation of the abstract runtime system for the Python backend.'''
  @property
  def Node(self):
    return Node

  @property
  def InfoTable(self):
    return InfoTable

  @property
  def prelude(self):
    from . import prelude
    return prelude

  @property
  def get_stepper(self):
    return get_stepper

  @property
  def get_step_counter(self):
    return StepCounter

  @property
  def evaluate(self):
    return lambda *args, **kwds: Evaluator(*args, **kwds).evaluate()

  @property
  def get_id(self):
    return get_id
