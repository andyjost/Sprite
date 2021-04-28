from __future__ import absolute_import
from .state import Evaluator, Frame, N, S, hnf, LEFT, RIGHT, UNDETERMINED, get_generator
from .transforms import Replacer, replace, replace_copy, rewrite
from .exceptions import *
from .graph import *
from .misc import *
from .... import runtime

__all__ = [
    'Runtime'

  # From misc.
  , 'freshvar'
  , 'freshvar_gen'
  , 'get_id'
  , 'get_stepper'
  , 'is_bound'
  , 'nextid'
  , 'StepCounter'

  # From state.
  , 'Evaluator'
  , 'Frame'
  , 'get_generator'
  , 'hnf'
  , 'LEFT'
  , 'N'
  , 'RIGHT'
  , 'S'
  , 'UNDETERMINED'

  # From graph.
  , 'T_FAIL', 'T_BIND', 'T_FREE', 'T_FWD', 'T_CHOICE', 'T_FUNC', 'T_CTOR'
  , 'InfoTable'
  , 'Node'

  # From transforms.
  , 'Replacer'
  , 'replace'
  , 'replace_copy'
  , 'rewrite'

  # From exceptions.
  , 'E_CONTINUE'
  , 'E_RESIDUAL'
  , 'E_STEPLIMIT'
  , 'E_UPDATE_CONTEXT'
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
