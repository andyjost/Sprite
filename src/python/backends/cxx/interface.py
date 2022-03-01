from ... import backends
from . import cyrt
from .compiler import compile, ir, materialize, render
# from ..generic import interface as generic

__all__ = ['Compiler', 'Runtime']

class Compiler(backends.Compiler):
  @property
  def IR(self):
    return ir.IR

  @property
  def compile(self):
    return compile.compile

  @property
  def materialize_function(self):
    return materialize.materialize

  @property
  def materialize_function_info_stub(self):
    return materialize.materialize_info_stub

  @property
  def materialize_type(self):
    return materialize.materialize_type

  @property
  def render(self):
    return render.render

# class Evaluator(generic.Evaluator):
#
#   def _make_rts(self, interp, goal):
#     assert False
#     # return state.RuntimeState(interp, goal)
#
#   def _eval(self):
#     assert False
#     # return fairscheme.D(self.rts)
#
#
# class Runtime(generic.Runtime):
#   '''
#   Implementation of the runtime system interface for the Python backend.  Used
#   by the Interpreter object.
#   '''
#   @property
#   def BACKEND_NAME(self):
#     return 'cxx'
#
#   @property
#   def Evaluator(self):
#     return Evaluator
#
#   @property
#   def Node(self):
#     return cyrt.Node
#
#   def get_interpreter_state(self, interp):
#     return interp._its
#
#   def init_interpreter_state(self, interp):
#     interp._its = cyrt.InterpreterState()
#
