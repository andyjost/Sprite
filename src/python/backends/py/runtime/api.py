from __future__ import absolute_import
from .fairscheme import D, N, S, hnf
from .state import Evaluator, Frame, LEFT, RIGHT, UNDETERMINED
from .transforms import Replacer, replace, replace_copy, rewrite, get_generator
from .graph import *
from .misc import *
from .... import runtime

__all__ = [
    'Runtime'

  # From fairscheme.
  , 'D'
  , 'N'
  , 'S'
  , 'hnf'

  # From graph.
  , 'InfoTable'
  , 'Node'

  # From misc.
  , 'freshvar'
  , 'freshvar_gen'
  , 'get_id'
  , 'get_stepper'
  , 'is_bound'
  , 'nextid'
  , 'StepCounter'
  , 'RuntimeException'
  , 'E_CONTINUE'
  , 'E_RESIDUAL'
  , 'E_STEPLIMIT'
  , 'E_UPDATE_CONTEXT'


  # From state.
  , 'Evaluator'
  , 'Frame'
  , 'LEFT'
  , 'RIGHT'
  , 'UNDETERMINED'

  # From transforms.
  , 'get_generator'
  , 'Replacer'
  , 'replace'
  , 'replace_copy'
  , 'rewrite'
  ]

class Runtime(runtime.Runtime):
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
