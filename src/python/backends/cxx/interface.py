from ... import backends
from . import cyrtbindings
from .compiler import compile, materialize, render

class IBackend(backends.IBackend):
  @property
  def compile(self):
    return compile.compile

  @property
  def evaluate(self):
    return cyrtbindings.evaluate

  def get_interpreter_state(self, interp):
    return interp._its

  def init_interpreter_state(self, interp):
    interp._its = cyrtbindings.InterpreterState()

  def init_module_state(self, moduleobj):
    moduleobj._cxx = cyrtbindings.Module.find_or_create(moduleobj.__name__)

  def link_function(self, info, function_spec, lazy):
    cyrtbindings.link_function(info, function_spec.materialize, lazy)

  def lookup_builtin_module(self, modulename):
    if modulename == 'Prelude':
      from ..cxx.currylib import prelude
      return prelude.PreludeSpecification
    elif modulename == 'Control.SetFunctions':
      from ..cxx.currylib import setfunctions
      return prelude.SetFunctionsSpecification

  @property
  def make_node(self):
    return cyrtbindings.make_node

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
    return cyrtbindings.single_step


