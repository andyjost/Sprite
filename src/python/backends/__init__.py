'''
Defines the BackendAPI object, which mediates interations between the Python
API and backends.

This contains definitions common to all backends and the interfaces each should
implement.
'''

from .. import common, config
import abc, importlib, six, weakref

__all__ = ['BackendAPI', 'InfoTable', 'InterpreterState', 'Node']

class BackendAPI(object):
  '''
  The interface to a Curry implementation.

  The context mediates all interactions bewteen the Sprite API (e.g., the
  Interpreter class) and a backend implementation.  The context is a singleton
  (each backend can have at most one).
  '''
  _instances = {}

  def __new__(cls, backend=None):
    if backend not in cls._instances:
      if cls is BackendAPI:
        assert backend is not None
        # Each backend must implement this class at
        # backends.<name>.api.BackendAPI.
        currypkg = config.python_package_name()
        api = importlib.import_module('%s.backends.%s.api' % (currypkg, backend))
        cls._instances[backend] = api.BackendAPI()
      else:
        return object.__new__(cls)
    return cls._instances[backend]

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

  @abc.abstractproperty
  def IR(self):
    '''The intermediate representation of a program.'''
    assert 0

  @abc.abstractproperty
  def compile(self):
    '''Converts ICurry to an instance of IR.'''
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
  def render(self):
    '''Converts the IR to a string.'''
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
  _fields_ = ['name', 'arity', 'tag', 'step', 'format', 'typecheck', 'typedef', 'flags']

  @property
  def is_special(self):
    return self.flags & 0xf

  @property
  def is_primitive(self):
    return self.typetag in \
        [common.F_INT_TYPE, common.F_CHAR_TYPE, common.F_FLOAT_TYPE]

  @property
  def typetag(self):
    return self.flags & 0xf

  @property
  def is_int(self):
    return self.typetag == common.F_INT_TYPE

  @property
  def is_char(self):
    return self.typetag == common.F_CHAR_TYPE

  @property
  def is_float(self):
    return self.typetag == common.F_FLOAT_TYPE

  @property
  def is_bool(self):
    return self.typetag == common.F_BOOL_TYPE

  @property
  def is_list(self):
    return self.typetag == common.F_LIST_TYPE

  @property
  def is_tuple(self):
    return self.typetag == common.F_TUPLE_TYPE

  @property
  def is_io(self):
    return self.typetag == common.F_IO_TYPE

  @property
  def is_partial(self):
    return self.typetag == common.F_PARTIAL_TYPE

  @property
  def is_monadic(self):
    return self.flags & common.F_MONADIC

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
