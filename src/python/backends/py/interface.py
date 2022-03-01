from .compiler import compile, ir, materialize, render
from .eval import evaluator
from ... import backends
import importlib

__all__ = ['IBackend']

class IBackend(backends.IBackend):
  @property
  def compile(self):
    return compile.compile

  @property
  def evaluate(self):
    return evaluator.evaluate

  def get_interpreter_state(self, interp):
    return interp._its

  def init_interpreter_state(self, interp):
    from .eval.rts import InterpreterState
    interp._its = InterpreterState()

  def init_module_state(self, moduleobj):
    pass

  def lookup_builtin_module(self, modulename):
    if modulename == 'Prelude':
      path = '.currylib.prelude'
      module = importlib.import_module(path, package=__package__)
      return module.PreludeSpecification
    elif modulename == 'Control.SetFunctions':
      path = '.currylib.setfunctions'
      module = importlib.import_module(path, package=__package__)
      return module.SetFunctionsSpecification

  @property
  def make_node(self):
    from .graph import Node
    return Node

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

  @property
  def single_step(self):
    return evaluator.single_step

