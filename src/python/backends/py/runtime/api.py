from .... import context
from . import fairscheme, state
from ...generic.runtime import api

__all__ = ['Runtime']

class Evaluator(api.Evaluator):

  def _make_rts(self, interp, goal):
    return state.RuntimeState(interp, goal)

  def _eval(self):
    return fairscheme.D(self.rts)


class Runtime(api.Runtime):
  '''
  Implementation of the runtime system interface for the Python backend.  Used
  by the Interpreter object.
  '''
  @property
  def BACKEND_NAME(self):
    return 'py'

  @property
  def Evaluator(self):
    return Evaluator

  @property
  def Node(self):
    from .graph import Node
    return Node

  @property
  def InfoTable(self):
    from .graph import InfoTable
    return InfoTable

  def get_interpreter_state(self, interp):
    return interp._its

  def init_interpreter_state(self, interp):
    from .state import InterpreterState
    interp._its = InterpreterState(interp)
