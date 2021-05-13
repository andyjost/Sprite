from .fairscheme import *
from .graph import *
from .misc import *
from .... import runtime

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


class Runtime(runtime.Runtime):
  '''Implementation of the abstract runtime system for the Python backend.'''
  def Node(self):
    return Node

  def InfoTable(self):
    return InfoTable

  def prelude(self):
    from . import prelude
    return prelude

  def get_stepper(self):
    return get_stepper()

  def get_step_counter(self):
    return StepCounter()
