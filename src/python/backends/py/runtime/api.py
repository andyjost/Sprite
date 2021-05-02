from __future__ import absolute_import
from .fairscheme import D, N, S, hnf
from .fairscheme.instance import get_generator
from .fairscheme.evaluator import Evaluator, Frame, LEFT, RIGHT, UNDETERMINED
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
  , 'Evaluator'
  , 'Frame'
  , 'LEFT'
  , 'RIGHT'
  , 'UNDETERMINED'
  , 'get_generator'

  # From graph.
  , 'InfoTable'
  , 'Node'
  , 'Replacer'
  , 'replace'
  , 'replace_copy'
  , 'rewrite'

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
