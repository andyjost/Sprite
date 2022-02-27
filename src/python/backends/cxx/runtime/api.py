from .... import context
from .. import cyrt
from ...generic.runtime import api

__all__ = ['Runtime']

class Evaluator(api.Evaluator):

  def _make_rts(self, interp, goal):
    assert False
    # return state.RuntimeState(interp, goal)

  def _eval(self):
    assert False
    # return fairscheme.D(self.rts)


class Runtime(api.Runtime):
  '''
  Implementation of the runtime system interface for the Python backend.  Used
  by the Interpreter object.
  '''
  @property
  def BACKEND_NAME(self):
    return 'cxx'

  @property
  def Evaluator(self):
    return Evaluator

  @property
  def Node(self):
    return cyrt.Node

  @property
  def InfoTable(self):
    return cyrt.InfoTable

  def get_interpreter_state(self, interp):
    return interp._its

  def init_interpreter_state(self, interp):
    interp._its = cyrt.InterpreterState()

