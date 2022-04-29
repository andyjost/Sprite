from ..generic.eval import evaluator
from ... import backends
from . import compiler, cyrtbindings, loader, materialize, toolchain
from ...objects.handle import getHandle

class IBackend(backends.IBackend):
  @property
  def backend_name(self):
    return 'cxx'

  @property
  def extend_plan_skeleton(self):
    return toolchain.extend_plan_skeleton

  @property
  def compile(self):
    return compiler.compile

  def get_interpreter_state(self, interp):
    return interp._its

  def init_interpreter_state(self, interp):
    interp._its = cyrtbindings.InterpreterState()

  def find_or_create_internal_module(self, moduleobj):
    h = getHandle(moduleobj)
    M = cyrtbindings.Module.find_or_create(h.fullname)
    M.link(h.icurry.metadata.get('cxx.shlib'))
    return M

  @property
  def load_module(self):
    return loader.load_module

  def lookup_builtin_module(self, modulename):
    if modulename == 'Prelude':
      from ..generic.currylib import prelude
      return prelude.PreludeSpecification()
    elif modulename == 'Control.SetFunctions':
      from ..generic.currylib import setfunctions
      return setfunctions.SetFunctionsSpecification()

  @property
  def create_evaluation_rts(self):
    return cyrtbindings.create_evaluation_rts

  @property
  def make_node(self):
    return cyrtbindings.make_node

  @property
  def materialize(self):
    return materialize.materialize

  @property
  def object_file_extension(self):
    return '.so'

  @property
  def write_module(self):
    return compiler.write_module


