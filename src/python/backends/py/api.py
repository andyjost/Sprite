from .compiler import compile, ir, materialize, render
from .eval import fairscheme, rts
from ..generic import api
from ... import context

__all__ = ['Compiler', 'Runtime']

class Compiler(context.Compiler):
  @property
  def IR(self):
    return ir.IR

  @property
  def compile(self):
    return compile.compile

  @property
  def materialize_function(self):
    return materialize.materialize_function

  @property
  def materialize_function_info_stub(self):
    return materialize.materialize_function_info_stub

  @property
  def materialize_type(self):
    return materialize.materialize_type

  @property
  def render(self):
    return render.render

class Evaluator(api.Evaluator):

  def _make_rts(self, interp, goal):
    return rts.RuntimeState(interp, goal)

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
    from .eval.rts import InterpreterState
    interp._its = InterpreterState(interp)
