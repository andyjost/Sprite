"""The public Python surface of Sprite.

Build typed terms with module calls, ``term`` and ``parse``. Evaluate them
with ``eval`` or ``solve`` and print values with ``show``. The installed
``__init__.pyi`` describes the public names and their landed signatures.
"""

# Install Sprite's breakpoint() as sys.breakpointhook.
import os
if os.environ.get('SPRITE_ENABLE_BREAKPOINT', False):
  from .utility import breakpoint
  del breakpoint

# Validate SPRITE_HOME.  When it is not set, the package finds its home from
# its own location, <home>/python/curry/__init__.py, which is the layout
# that make install writes.
if 'SPRITE_HOME' not in os.environ:
  _home = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
  _resource_home = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_sprite')
  if os.path.isdir(os.path.join(_resource_home, 'sysconfig')):
    _home = _resource_home
  del _resource_home
  if os.path.isdir(os.path.join(_home, 'sysconfig')):
    os.environ['SPRITE_HOME'] = _home
  del _home
if 'SPRITE_HOME' not in os.environ:
  raise ImportError('SPRITE_HOME is not set in the environment')
if not os.path.isdir(os.environ['SPRITE_HOME']):
  raise ImportError('SPRITE_HOME is not a directory')
if not os.access(os.environ['SPRITE_HOME'], os.R_OK):
  raise ImportError('SPRITE_HOME is not readable')
del os

from .exceptions import (
    CurryError, CompileError, NotConstructorError, ModuleLookupError
  , SymbolLookupError, TypeLookupError, CurryIndexError, CurryTypeError
  , TypeSyntaxError, InterfaceError, ModuleExistsError, LoadError
  , FlagError, CurryWarning, IntOverflowError, NoValueError
  , ManyValuesError, StaleError, PrerequisiteError, EvaluationError
  , SuspensionError, DivisionByZeroError, CurryIOError, CurryFileNotFoundError
  , NondetError, StackLimitError, EvaluationTimeout, InstantiationError
  )
from . import interpreter, lib
from .interpreter import flags as _flags

# A reload replaces the interpreter.  Release the previous one's expression
# modules first, so their libraries unload now; see interpreter/compile.py.
if '_interpreter_' in globals():
  if _interpreter_.flags['backend'] == 'cxx':
    from .backends.cxx import tiered as _tiered
    _tiered.cancel()
    _tiered.wait(interp=_interpreter_)
  _interpreter_._session = object()
  _interpreter_._expression_modules = []
  _interpreter_._unlink_modules()
  _old_prelude = _interpreter_.modules.pop('Prelude', None)
  if _old_prelude is not None:
    _interpreter_.backend.module_unlinked(_interpreter_, _old_prelude)
  del _old_prelude
try:
  _interpreter_ = interpreter.Interpreter(flags=globals().pop('_reload_flags', _flags.getflags()))
except FlagError:
  import sys as _sys
  def _flag_error_hook(kind, value, traceback, previous=_sys.excepthook):
    if issubclass(kind, FlagError):
      print('FlagError: ' + str(value), file=_sys.stderr)
    else:
      previous(kind, value, traceback)
  _sys.excepthook = _flag_error_hook
  raise

from .interpreter import session as _session

def compile(source, *, name=None, imports=()):
  return _session.compile(_interpreter_, source, name=name, imports=imports)

def eval(goal):
  """Return the converted values of a goal as a lazy Results."""
  return _interpreter_.eval(goal)

def solve(goal):
  return _interpreter_.solve(goal)

def stream(action):
  """Return the ordered values yielded by a lazy I/O action as a Stream."""
  return _interpreter_.stream(action)
flags = _session.Flags(_interpreter_)
def import_(name, *, path=None):
  return _session.import_(_interpreter_, name, path=path)

def load(path):
  return _session.load(_interpreter_, path)

modules = _session.Modules(_interpreter_)

path = _interpreter_.path

def reset(**flags):
  return _session.reset(_interpreter_, **flags)

def save(module, path, *, main=None):
  return _session.save(_interpreter_, module, path, main=main)

def wait(module=None):
  return _session.wait(_interpreter_, module)
def stats():
  return _interpreter_.stats()
from .objects import CurryModule as Module
from .objects.terms import (
    Term, Data, DataClass, ConstructorClass, Function, Values, Symbol, DataType, Char
  , Var, Anonymous, anonymous, Reference
  )
from .typecheck.errors import ConversionError, MismatchError, ArityError, NoInstanceError
from .typecheck.defaulting import DefaultingError

def info(module):
  from .objects.terms import check_module
  check_module(module)
  return getattr(module, '.info')

def term(value, *, type=None):
  from .objects.terms import term as build_term
  return build_term(_interpreter_, value, type)

def parse(text, *, imports=()):
  from .objects.terms import parse as parse_term
  return parse_term(_interpreter_, text, imports)

def free(name=None, *, type=None):
  return Var(_interpreter_, name, type)

def choice(first, second, *more):
  from .objects.terms import choice as build_choice
  return build_choice(_interpreter_, first, second, *more)

def let(body, /, **bindings):
  from .objects.terms import let as build_let
  return build_let(_interpreter_, body, bindings)

def ref(name):
  return Reference(_interpreter_, name)

def _qualified(name):
  from .utility.curryname import isLegalModulename
  parts = name.split('.')
  for index in range(len(parts) - 1, 0, -1):
    prefix = '.'.join(parts[:index])
    if not isLegalModulename(prefix):
      continue
    try:
      module = import_(prefix)
    except ModuleLookupError:
      continue
    return module, '.'.join(parts[index:])
  raise ModuleLookupError('no module prefix in %r' % name)

def symbol(name):
  module, local = _qualified(name)
  return module[local]
def type(name):
  module, local = _qualified(name)
  try:
    return info(module).types[local]
  except KeyError:
    raise TypeLookupError('module %r has no type %r' % (module.__name__, local)) from None
def typeof(value, *, defaulted=False):
  if isinstance(value, str):
    value = term(value)
  return _interpreter_.typeof(value, defaulted=defaulted)

def reload(module, *, text=None):
  return _session.reload(_interpreter_, module, text=text)


from .objects.results import Results, Answer, Bindings, Stream
# Load the node printer before exporting the public function of that name.
from .show import show as _show_node

def show(value):
  if isinstance(value, (Answer, Bindings)):
    return str(value)
  from .objects.termshow import show as show_term
  return show_term(value)


__all__ = [
    'import_'
  , 'compile'
  , 'reload'
  , 'reset'
  , 'save'
  , 'load'
  , 'modules'
  , 'path'
  , 'flags'
  , 'wait'
  , 'stats'
  , 'term'
  , 'parse'
  , 'free'
  , 'anonymous'
  , 'choice'
  , 'let'
  , 'ref'
  , 'symbol'
  , 'type'
  , 'eval'
  , 'solve'
  , 'stream'
  , 'typeof'
  , 'show'
  , 'Module'
  , 'Symbol'
  , 'DataType'
  , 'Term'
  , 'Data'
  , 'DataClass'
  , 'ConstructorClass'
  , 'Function'
  , 'Var'
  , 'Values'
  , 'Char'
  , 'Anonymous'
  , 'Results'
  , 'Stream'
  , 'Answer'
  , 'Bindings'
  , 'CurryError'
  , 'CurryWarning'
  , 'CurryTypeError'
  , 'ConversionError'
  , 'MismatchError'
  , 'ArityError'
  , 'NoInstanceError'
  , 'DefaultingError'
  , 'TypeSyntaxError'
  , 'InterfaceError'
  , 'IntOverflowError'
  , 'CompileError'
  , 'EvaluationError'
  , 'SuspensionError'
  , 'DivisionByZeroError'
  , 'CurryIOError'
  , 'CurryFileNotFoundError'
  , 'NondetError'
  , 'StackLimitError'
  , 'EvaluationTimeout'
  , 'InstantiationError'
  , 'NoValueError'
  , 'ManyValuesError'
  , 'ModuleLookupError'
  , 'ModuleExistsError'
  , 'SymbolLookupError'
  , 'TypeLookupError'
  , 'StaleError'
  , 'LoadError'
  , 'PrerequisiteError'
  , 'FlagError'
  , 'NotConstructorError'
  , 'CurryIndexError'
  , 'info'
  , 'Reference'
  ]


# Forward assignment as well as mutation of the public search path.
import types as _types
import sys as _sys

class _Package(_types.ModuleType):
  def __setattr__(self, name, value):
    if name == 'path':
      self._interpreter_.path = value
      value = self._interpreter_.path
    super().__setattr__(name, value)

_sys.modules[__name__].__class__ = _Package
