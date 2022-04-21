from ... import backends
from . import compiler, cyrtbindings, materialize, plan

class IBackend(backends.IBackend):
  @property
  def backend_name(self):
    return 'cxx'

  @property
  def extend_plan_skeleton(self):
    return plan.extend_plan_skeleton

  @property
  def compile(self):
    return compiler.compile

  @property
  def evaluate(self):
    return cyrtbindings.evaluate

  def get_interpreter_state(self, interp):
    return interp._its

  def init_interpreter_state(self, interp):
    interp._its = cyrtbindings.InterpreterState()

  def find_or_create_internal_module(self, moduleobj):
    return cyrtbindings.Module.find_or_create(moduleobj.__name__)

  def lookup_builtin_module(self, modulename):
    if modulename == 'Prelude':
      from ..cxx.currylib import prelude
      return prelude.PreludeSpecification()
    elif modulename == 'Control.SetFunctions':
      from ..cxx.currylib import setfunctions
      return setfunctions.SetFunctionsSpecification()

  @property
  def make_node(self):
    return cyrtbindings.make_node

  @property
  def materialize(self):
    return materialize.materialize

  @property
  def single_step(self):
    return cyrtbindings.single_step

  @property
  def write_module(self):
    return compiler.write_module


