from ..generic.eval import evaluator
from ... import backends
from . import (
    compiler, cyrtbindings, fundamental_symbols, implementation, loader
  , materialize, tiered, toolchain
  )
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
    # A new interpreter and a reset unload the modules whose compiles run in
    # the background.
    tiered.cancel()
    interp._its = cyrtbindings.InterpreterState()

  def module_loaded(self, interp, moduleobj, currypath):
    tiered.module_loaded(interp, moduleobj, currypath)

  def before_evaluation(self, interp):
    if tiered.enabled(interp):
      tiered.poll(interp)

  def after_evaluation(self, interp):
    if tiered.enabled(interp):
      tiered.poll(interp)

  def tiered_counts(self):
    return tiered.counts()

  def num_collections(self):
    return cyrtbindings.gc_collections()

  def gc_seconds(self):
    return cyrtbindings.gc_seconds()

  def gc_counters(self):
    return cyrtbindings.gc_counters()

  def scheduler_counters_enabled(self):
    return cyrtbindings.scheduler_counters_enabled()

  def getimpl(self, symbol):
    return implementation.getimpl(symbol)

  def find_or_create_internal_module(self, moduleobj):
    h = getHandle(moduleobj)
    M = cyrtbindings.Module.find_or_create(h.fullname)
    M.link(h.icurry.metadata.get('cxx.shlib'))
    return M

  @property
  def fundamental_symbols(self):
    return fundamental_symbols

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
    return cyrtbindings.RuntimeState

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


