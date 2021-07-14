from .fairscheme import *
from .graph import *
from .misc import *
from .... import context
import itertools

FAIR_SCHEME_VERSION = 2

if FAIR_SCHEME_VERSION == 2:
  from .fairscheme.v2.algorithm import hnf
  from .fairscheme.v2.evaluator import Evaluator
  from .fairscheme.v2.state import InterpreterState, RuntimeState

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
  , 'E_CONTINUE', 'E_RESIDUAL', 'E_STEPLIMIT', 'E_TERMINATE'
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
  def get_id(self): # How does this function make sense?  We need the frame to get the representative ID.
    return get_id


class FairSchemeAPI(object):
  '''
  Internal interface used to switch between implementations of the Fair Scheme.
  Using this, the built-in libraries and compiler can avoid dependencies on a
  particular version.
  '''
  @staticmethod
  def hnf():
    return hnf

  @staticmethod
  def get_generator():
    from .fairscheme.freevars import get_generator
    return get_generator

