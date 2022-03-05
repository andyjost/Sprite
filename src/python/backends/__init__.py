'''
Defines the IBackend object, which mediates interations between the Python
API and backends.

This contains definitions common to all backends and the interfaces each should
implement.
'''

from .. import config
import abc, importlib, six

__all__ = ['IBackend', 'Node']

class IBackend(six.with_metaclass(abc.ABCMeta)):
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
  def compile(self):
    '''Converts ICurry to an instance of IR.'''
    assert 0

  @abc.abstractproperty
  def evaluate(self):
    pass

  @abc.abstractmethod
  def get_interpreter_state(self, interp):
    '''Gets the runtime-specific state attached to an interpreter.'''
    assert 0

  @abc.abstractmethod
  def init_module_state(self, moduleobj):
    assert 0

  @abc.abstractmethod
  def init_interpreter_state(self, interp):
    '''Initializes an interpreter with the runtime-specific state.'''
    assert 0

  @abc.abstractmethod
  def link_function(self, info, function_spec, lazy):
    '''Link a function (or trampoline) into the info table.'''
    assert 0

  @abc.abstractmethod
  def lookup_builtin_module(self, modulename):
    '''Looks up the implementation for a built-in module.'''
    assert 0

  @abc.abstractproperty
  def make_node(self):
    assert 0

  @abc.abstractproperty
  def materialize_function(self):
    '''Converts the IR to runnable code.'''
    assert 0

  @abc.abstractproperty
  def materialize_function_info_stub(self):
    '''
    Generates a function info table with the step function set to a compile
    hook.
    '''
    assert 0

  @abc.abstractproperty
  def materialize_type(self):
    '''Converts the IR to a type.'''
    assert 0

  @abc.abstractproperty
  def save_module(self):
    '''Save a Curry module into a Python package.'''
    assert 0

  @abc.abstractproperty
  def single_step(self):
    '''Performs a single step on an expression.'''
    assert 0


# Each backend must provide a Node object and register it with this class.
class Node(six.with_metaclass(abc.ABCMeta)):
  pass

