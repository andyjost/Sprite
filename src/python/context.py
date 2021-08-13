'''
Defines the context object, which mediates interations between the Python API
and a backend.

This contains definitions common to all backends and the interfaces each should
implement.
'''

from . import config
import abc
import importlib

__all__ = ['Compiler', 'Context', 'InfoTable', 'Node', 'Runtime']

class Context(object):
  '''
  The interface to a Curry implementation.

  The context mediates all interactions bewteen the Sprite API (e.g., the
  Interpreter class) and a backend implementation.  The context is a singleton
  (each backend can have at most one).
  '''
  _instances = {}
  def __new__(cls, backend=None):
    if backend not in cls._instances:
      self = object.__new__(cls)
      self._backend = backend if backend is not None else config.backend()
      self._runtime = Runtime(self._backend)
      self._compiler = Compiler(self._backend)
      cls._instances[self._backend] = self
      if backend is None:
        cls._instances[None] = self
    return cls._instances[backend]

  @property
  def backend(self):
    return self._backend

  @property
  def compiler(self):
    return self._compiler

  @property
  def runtime(self):
    return self._runtime


class Runtime(object):
  '''Abstract interface for a runtime system.'''
  __metaclass__ = abc.ABCMeta

  def __new__(cls, backend='py'):
    if cls is Runtime:
      # Each backend must implement this class at
      # backends/<name>/runtime.api.Runtime.
      currypkg = config.python_package_name()
      api = importlib.import_module('%s.backends.%s.runtime.api' % (currypkg, backend))
      return api.Runtime()
    else:
      return object.__new__(cls)

  @abc.abstractproperty
  def Node(self):
    assert 0

  @abc.abstractproperty
  def InfoTable(self):
    assert 0

  @abc.abstractmethod
  def init_interpreter_state(self, interp):
    assert 0

  @abc.abstractmethod
  def get_interpreter_state(self, interp):
    assert 0

  @abc.abstractproperty
  def prelude(self):
    assert 0

  @abc.abstractproperty
  def evaluate(self):
    assert 0

  @abc.abstractmethod
  def single_step(self, interp, expr):
    assert 0

# Each backend must provide a Node object and register it with this class.
class Node(object):
  __metaclass__ = abc.ABCMeta


# Each backend must provide an InterpreterState object and register it with this
# class.
class InterpreterState(object):
  __metaclass__ = abc.ABCMeta

# Each backend must provide an InfoTable object and register it with this
# class.
class InfoTable(object):
  __metaclass__ = abc.ABCMeta


class Compiler(object):
  '''Abstract interface for an ICurry compiler.'''
  __metaclass__ = abc.ABCMeta

  def __new__(cls, backend='py'):
    # Each backend must implement this class at
    # backends/<name>/compiler.api.Compiler.
    if cls is Compiler:
      currypkg = config.python_package_name()
      api = importlib.import_module('%s.backends.%s.compiler.api' % (currypkg, backend))
      return api.Compiler()
    else:
      return object.__new__(cls)

  @abc.abstractproperty
  def compile_function(self):
    assert 0

