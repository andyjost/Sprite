from . import compiler
from .compiler_old import materialize as materialize_old
from . import materialize
from .eval import evaluator
from .graph import Node
from ... import backends
import importlib

__all__ = ['IBackend']

class IBackend(backends.IBackend):
  @property
  def backend_name(self):
    return 'py'

  @property
  def target_suffix(self):
    return '.py'

  @property
  def compile(self):
    return compiler.compile

  @property
  def evaluate(self):
    return evaluator.evaluate

  def get_interpreter_state(self, interp):
    return interp._its

  def init_interpreter_state(self, interp):
    from .eval.rts import InterpreterState
    interp._its = InterpreterState()

  def find_or_create_module(self, moduleobj):
    pass

  def link_function(self, info, function_spec, lazy):
    if lazy:
      info.step = function_spec
    else:
      info.step = function_spec.materialize()

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
  def make_node(self):
    return Node

  @property
  def materialize(self):
    return materialize.materialize

  @property
  def materialize_function(self):
    return materialize_old.materialize_function

  @property
  def materialize_function_info_stub(self):
    return materialize_old.materialize_function_info_stub

  @property
  def materialize_type(self):
    return materialize_old.materialize_type

  @property
  def single_step(self):
    return evaluator.single_step

  @property
  def write_module(self):
    return compiler.write_module
