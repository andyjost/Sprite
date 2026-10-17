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
  _interpreter_._session = object()
  _interpreter_._expression_modules = []
  _interpreter_._unlink_modules()
  _old_prelude = _interpreter_.modules.pop('Prelude', None)
  if _old_prelude is not None:
    _interpreter_.backend.module_unlinked(_interpreter_, _old_prelude)
  del _old_prelude
_interpreter_ = interpreter.Interpreter(flags=_flags.getflags())

compile = _interpreter_.compile

def eval(goal):
  """Return the converted values of a goal as a lazy Results."""
  return _interpreter_.eval(goal)

solve = _interpreter_.solve
flags = _interpreter_.flags
'''
The ``flags`` attribute of the global interpreter.  Change its entries in
place to reconfigure the interpreter, ``curry.flags['trace'] = True``.
An assignment to ``curry.flags`` rebinds the name in the package and changes
nothing in the interpreter.

:meta hide-value:
'''
import_ = _interpreter_.import_
load = _interpreter_.load
modules = _interpreter_.modules
'''
The ``modules`` attribute of the global interpreter.  This is a ``dict`` that
contains the imported Curry modules.

:meta hide-value:
'''

path = _interpreter_.path
'''
The ``path`` attribute of the global interpreter.  Initialized from environment
variable CURRYPATH.  Change it in place to adjust the Curry search path,
``curry.path.insert(0, '.')``.  An assignment to ``curry.path`` rebinds the
name in the package and changes nothing in the interpreter.

:meta hide-value:
'''

reset = _interpreter_.reset
save = _interpreter_.save
stats = _interpreter_.stats
from .objects import CurryModule as Module
from .objects.terms import (
    Term, Data, Function, Values, Symbol, DataType, Char
  , Var, Anonymous, anonymous, Reference
  )
from .typecheck.errors import ConversionError, MismatchError, ArityError, NoInstanceError
from .typecheck.defaulting import DefaultingError

def info(module):
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

def reload(flags={}):
  '''
  Hard-resets the interpreter.  Any flags supplied will be forwarded to the
  constructor, overriding flags supplied via the environment variable
  SPRITE_INTERPRETER_FLAGS.
  '''
  interpreter.reload(__name__, flags)


from .objects.results import Results, Answer, Bindings
# Load the node printer before exporting the public function of that name.
from .show import show as _show_node

def show(value):
  if isinstance(value, (Answer, Bindings)):
    return str(value)
  from .objects.termshow import show as show_term
  return show_term(value)


# wait belongs to lane 5; stream and Stream belong to lane 7.
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
  , 'typeof'
  , 'show'
  , 'Module'
  , 'Symbol'
  , 'DataType'
  , 'Term'
  , 'Data'
  , 'Function'
  , 'Var'
  , 'Values'
  , 'Char'
  , 'Anonymous'
  , 'Results'
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
