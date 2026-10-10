'''
Defines the IBackend object, which mediates interations between the Python
API and backends.

This contains definitions common to all backends and the interfaces each should
implement.
'''

from .. import config
import abc, importlib

__all__ = ['IBackend', 'Node']

class IBackend(metaclass=abc.ABCMeta):
  '''
  The interface to a Curry implementation.

  This interface mediates all interactions bewteen the Sprite API (e.g., the
  Interpreter class) and a backend implementation.  This stateless object
  is shared among all interpreters using the same backend.
  '''
  _instances = {}

  def __new__(cls, backend=None):
    if backend not in cls._instances:
      if cls is IBackend:
        assert backend is not None
        # Each backend must implement this class at backends.<name>.interface.IBackend.
        currypkg = config.python_package_name()
        ifc = importlib.import_module('%s.backends.%s.interface' % (currypkg, backend))
        cls._instances[backend] = ifc.IBackend()
      else:
        return object.__new__(cls)
    return cls._instances[backend]

  @abc.abstractproperty
  def backend_name(self):
    '''E.g., 'py' or 'cxx'.'''
    assert 0

  @abc.abstractproperty
  def extend_plan_skeleton(self):
    assert 0

  @abc.abstractproperty
  def compile(self):
    '''Converts ICurry to an instance of IR.'''
    assert 0

  @abc.abstractmethod
  def get_interpreter_state(self, interp):
    '''Gets the runtime-specific state attached to an interpreter.'''
    assert 0

  @abc.abstractmethod
  def find_or_create_internal_module(self, moduleobj):
    assert 0

  def compile_pending(self, moduleobj):
    '''
    Compiles the functions of a loaded module whose compilation the backend
    deferred, once every symbol of the module is registered.  The Python
    backend compiles a step function on its first call; an expression module
    (compile.compile_expression) leaves the registry of the interpreter after
    this call, so its functions are compiled here.  A backend that compiles
    whole modules ahead of time has nothing to do.
    '''

  def module_loaded(self, interp, moduleobj, currypath):
    '''
    Called when the import of a module ends, after the imports of the module
    were imported and its symbols were loaded.  ``currypath`` is the search
    path of the import.  The C++ backend queues the background compile of a
    module it interprets (see backends.cxx.tiered).
    '''

  def module_unlinked(self, interp, moduleobj):
    '''
    Called when a module leaves the interpreter (Handle.unlink: a reset, or
    the hard reset of ``reload``), after its name left ``interp.modules``.
    The module object may stay alive in the hands of the user.  The C++
    backend hands the tables of the module to the kept store of the
    runtime, so a module of the same name made later runs its own code
    (issue #114; see Module::retire in cyrt/module.hpp).
    '''

  def before_evaluation(self, interp):
    '''
    Called when an evaluation is about to start.  The C++ backend applies the
    compiled objects that finished in the background.
    '''

  def after_evaluation(self, interp):
    '''
    Called when the values of an evaluation are exhausted.  The C++ backend
    applies and logs the compiled objects that finished during the
    evaluation.
    '''

  def tiered_counts(self):
    '''
    The functions swapped to compiled code and the background compiles that
    failed in this process (Interpreter.stats reports them).  A backend
    without tiered execution answers zeros.
    '''
    return 0, 0

  @abc.abstractproperty
  def fundamental_symbols(self):
    assert 0

  @abc.abstractmethod
  def init_interpreter_state(self, interp):
    '''Initializes an interpreter with the runtime-specific state.'''
    assert 0

  def num_collections(self):
    '''
    The number of collections the garbage collector of this backend has run
    in this process.  A backend without a collector of its own answers zero.
    '''
    return 0

  def gc_seconds(self):
    '''
    The seconds the garbage collector of this backend has spent in its
    collections in this process.  A backend without a collector of its own
    answers zero.
    '''
    return 0.0

  def gc_counters(self):
    '''
    The counters of the garbage collector of this backend, summed over its
    collections in this process, as a dict keyed by the names in
    stats.GC_COUNTERS (the seconds of the phases of a collection, the nodes
    marked by age, the configurations pushed, the queues and configurations
    destroyed, the writes into old nodes).  A backend without a collector
    of its own answers an empty dict, which Interpreter.stats reports as
    zeros.
    '''
    return {}

  def scheduler_counters_enabled(self):
    '''
    True when the runtime of this backend counts the serial steps, the
    lifetimes of configurations, and the shared work of an evaluation
    (Interpreter.stats reports them).  Only the C++ runtime built with
    make COUNTERS=1 does.
    '''
    return False

  def getimpl(self, symbol):
    '''
    The implementation code of the step function of ``symbol`` (a
    CurryNodeInfo) as text; see :func:`curry.inspect.getimpl`.  Raises
    ValueError when the backend has no code for the symbol.
    '''
    raise ValueError(
        'no implementation code available for %r' % symbol.fullname
      )

  @abc.abstractproperty
  def load_module(self):
    '''Load the contents of a Curry module.'''
    assert 0

  @abc.abstractmethod
  def lookup_builtin_module(self, modulename):
    '''Looks up the implementation for a built-in module.'''
    assert 0

  @abc.abstractproperty
  def create_evaluation_rts(self):
    '''Creates a new runtime state representing an evaluation.'''
    assert 0

  @abc.abstractproperty
  def make_node(self):
    assert 0

  @abc.abstractproperty
  def materialize(self):
    assert 0

  @abc.abstractproperty
  def object_file_extension(self):
    assert 0

  @abc.abstractproperty
  def write_module(self):
    '''Write the contents of a Curry module to a stream.'''
    assert 0


# Each backend must provide a Node object and register it with this class.
class Node(metaclass=abc.ABCMeta):
  pass

# Each backend must provide an InfoTable object and register it with this class.
class InfoTable(metaclass=abc.ABCMeta):
  pass

