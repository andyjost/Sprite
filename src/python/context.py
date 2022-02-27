from __future__ import absolute_import
'''
Defines the context object, which mediates interations between the Python API
and a backend.

This contains definitions common to all backends and the interfaces each should
implement.
'''

from . import config
import abc, importlib, six, weakref
from .backends.generic.compiler import materialize

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


class Runtime(six.with_metaclass(abc.ABCMeta)):
  '''Abstract interface for a runtime system.'''
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
    '''Represents a Curry expression.'''
    assert 0

  @abc.abstractproperty
  def InfoTable(self):
    '''Stores compiler-generated symbol information.'''
    assert 0

  @abc.abstractmethod
  def evaluate(self, interp, goal):
    pass

  @abc.abstractproperty
  def Evaluator(self):
    '''Evaluates a Curry expression.'''
    assert 0

  @abc.abstractmethod
  def get_interpreter_state(self, interp):
    '''Gets the runtime-specific state attached to an interpreter.'''
    assert 0

  @abc.abstractmethod
  def init_interpreter_state(self, interp):
    '''Initializes an interpreter with the runtime-specific state.'''
    assert 0

  @abc.abstractmethod
  def lookup_builtin_module(self):
    '''Looks up the implementation for a built-in module.'''
    assert 0

  @abc.abstractmethod
  def single_step(self, interp, expr):
    '''Performs a single step on an expression.'''
    assert 0

# Each backend must provide a Node object and register it with this class.
class Node(six.with_metaclass(abc.ABCMeta)):
  pass

# Each backend must provide an InterpreterState object and register it with
# this class.  This is an opaque type that may contain whatever the backend
# needs.
class InterpreterState(six.with_metaclass(abc.ABCMeta)):
  pass

# Each backend must provide an InfoTable derived from this class.
class InfoTable(object):
  from .common import (
      INT_TYPE, CHAR_TYPE, FLOAT_TYPE, BOOL_TYPE, LIST_TYPE, TUPLE_TYPE
    , IO_TYPE, PARTIAL_TYPE, OPERATOR, MONADIC
    )

  _fields_ = ['name', 'arity', 'tag', 'step', 'format', 'typecheck', 'typedef', 'flags']

  @property
  def is_special(self):
    return self.flags & 0xf

  @property
  def is_primitive(self):
    return (self.flags & 0xf) in [self.INT_TYPE, self.CHAR_TYPE, self.FLOAT_TYPE]

  @property
  def is_int(self):
    return (self.flags & 0xf) == self.INT_TYPE

  @property
  def is_char(self):
    return (self.flags & 0xf) == self.CHAR_TYPE

  @property
  def is_float(self):
    return (self.flags & 0xf) == self.FLOAT_TYPE

  @property
  def is_bool(self):
    return (self.flags & 0xf) == InfoTable.BOOL_TYPE

  @property
  def is_list(self):
    return (self.flags & 0xf) == InfoTable.LIST_TYPE

  @property
  def is_tuple(self):
    return (self.flags & 0xf) == InfoTable.TUPLE_TYPE

  @property
  def is_io(self):
    return (self.flags & 0xf) == InfoTable.IO_TYPE

  @property
  def is_partial(self):
    return (self.flags & 0xf) == InfoTable.PARTIAL_TYPE

  @property
  def is_monadic(self):
    return self.flags & InfoTable.MONADIC

  def __str__(self):
    return 'Info for %r' % self.name

  def __repr__(self):
    show = lambda x: repr(x()) if isinstance(x, weakref.ref) else repr(x)
    return ''.join([
        'InfoTable('
      , ', '.join(
            '%s=%s' % (field, show(getattr(self, field)))
                for field in self._fields_
          )
      , ')'
      ])


class Compiler(six.with_metaclass(abc.ABCMeta)):
  '''Abstract interface for an ICurry compiler.'''

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
  def IR(self):
    '''The intermediate representation of a program.'''
    assert 0

  @abc.abstractproperty
  def compile(self):
    '''Converts ICurry to an instance of IR.'''
    assert 0

  @abc.abstractproperty
  def materialize(self):
    '''Converts the IR to runnable code.'''
    assert 0

  @abc.abstractproperty
  def render(self):
    '''Converts the IR to a string.'''
    assert 0

  @property
  def materialize_type(self):
    return materialize.materialize_type

  @property
  def materialize_function_info_stub(self):
    return materialize.materialize_function_info_stub

