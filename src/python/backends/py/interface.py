from .currylib import fundamental
from ..generic.eval import evaluator
from .graph import Node
from ... import backends
from . import compiler, loader, materialize, toolchain
import importlib

__all__ = ['IBackend']

class IBackend(backends.IBackend):
  @property
  def backend_name(self):
    return 'py'

  @property
  def extend_plan_skeleton(self):
    return toolchain.extend_plan_skeleton

  @property
  def compile(self):
    return compiler.compile

  def get_interpreter_state(self, interp):
    return interp._its

  def init_interpreter_state(self, interp):
    from .eval.rts import InterpreterState
    interp._its = InterpreterState()

  def find_or_create_internal_module(self, moduleobj):
    pass

  @property
  def fundamental_symbols(self):
    return fundamental

  @property
  def load_module(self):
    return loader.load_module

  def lookup_builtin_module(self, modulename):
    if modulename == 'Prelude':
      path = '.currylib.prelude'
      module = importlib.import_module(path, package=__package__)
      return module.PreludeSpecification()
    elif modulename == 'Control.SetFunctions':
      path = '.currylib.setfunctions'
      module = importlib.import_module(path, package=__package__)
      return module.SetFunctionsSpecification()

  @property
  def create_evaluation_rts(self):
    from .eval import rts
    return rts.RuntimeState

  @property
  def make_node(self):
    return Node

  @property
  def materialize(self):
    return materialize.materialize

  @property
  def object_file_extension(self):
    return '.py'

  @property
  def write_module(self):
    return compiler.write_module

