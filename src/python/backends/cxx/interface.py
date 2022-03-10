from ... import backends
from . import cyrtbindings
from .compiler import compile, materialize, save

class IBackend(backends.IBackend):
  @property
  def backend_name(self):
    return 'cxx'

  @property
  def target_suffix(self):
    return '.cpp'

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

  def find_or_create_module(self, moduleobj):
    return cyrtbindings.Module.find_or_create(moduleobj.__name__)

  def link_function(self, info, function_spec, lazy):
    cyrtbindings.link_function(info, function_spec, lazy)

  def lookup_builtin_module(self, modulename):
    if modulename == 'Prelude':
      from ..cxx.currylib import prelude
      return prelude.PreludeSpecification
    elif modulename == 'Control.SetFunctions':
      from ..cxx.currylib import setfunctions
      return setfunctions.SetFunctionsSpecification

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
  def save_module(self):
    return save.save_module

  @property
  def single_step(self):
    return cyrtbindings.single_step


