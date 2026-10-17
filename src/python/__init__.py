'''
The Sprite Curry system.

This package contains everything one needs to compile and execute Curry code.
The topmost module provides an instance of the Curry system and an API to
interact with it.

To perform a soft reset call :func:`reset`.  This returns the system to its
original state, with no definitions and no modules imported.  The configuration
is taken from environment variable SPRITE_INTERPRETER_FLAGS.  To change that at
runtime, call :func:`reload` and specify new flags.

Use :func:`import_` to import Curry modules, :func:`compile` to compile Curry
code, :func:`expr` to build Curry expressions, and :func:`eval` to evaluate
them.  :data:`path` determines where Sprite searches for Curry code.  Loaded
modules can be found under :data:`modules`.  Use :func:`topython` to convert
Curry values to Python objects.  :func:`stats` reports the statistics of the
run: time, rewrite steps, forks, collections, memory, compile time, and
collector time.

Example:

    >>> mymodule = curry.compile("""
    ... data Item = A | B
    ... rotate A = B
    ... rotate B = A
    ... main :: Item
    ... main = rotate A ? rotate B
    ... """)
    >>> for value in curry.eval(mymodule.main):
    ...   print(value)
    B
    A
'''

__all__ = [
  # Global API
    'getInterpreter'
  , 'CurryError'
  , 'reload'
  , 'show_value'

  # Methods of the global interpreter.
  , 'compile'
  , 'currytype'
  , 'describe'
  , 'eval'
  , 'expr'
  , 'flags'
  , 'import_'
  , 'load'
  , 'module'
  , 'modules'
  , 'path'
  , 'raw_expr'
  , 'reset'
  , 'save'
  , 'stats'
  , 'symbol'
  , 'topython'
  , 'type'
  , 'typeof'

  # Wrappers to control expression building.
  , 'choice'
  , 'cons'
  , 'fail'
  , 'free'
  , 'nil'
  , 'ref'
  , 'typed'
  , 'unboxed'
  ]

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

from .exceptions import *
from . import interpreter, lib
from .interpreter import flags as _flags
from .utility import visitation as _visitation
import collections.abc as _collections_abc

from . import expressions as _expressions
choice  = _expressions.choice
cons    = _expressions.cons
fail    = _expressions.fail
'''
Places a failure into a Curry expression.

:meta hide-value:
'''
free    = _expressions.free
nil     = _expressions.nil
'''
Places a list terminator into a Curry expression.

:meta hide-value:
'''
ref     = _expressions.ref
typed   = _expressions.typed
unboxed = _expressions.unboxed
del _expressions

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
currytype = _interpreter_.currytype
describe = _interpreter_.describe
eval = _interpreter_.eval
solve = _interpreter_.solve
expr = _interpreter_.expr
flags = _interpreter_.flags
'''
The ``flags`` attribute of the global interpreter.  Change its entries in
place to reconfigure the interpreter, ``curry.flags['defaultconverter'] =
'topython'``.  An assignment to ``curry.flags`` rebinds the name in the
package and changes nothing in the interpreter.

:meta hide-value:
'''
import_ = _interpreter_.import_
load = _interpreter_.load
module = _interpreter_.module
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

raw_expr = _interpreter_.raw_expr
reset = _interpreter_.reset
save = _interpreter_.save
stats = _interpreter_.stats
from .objects import CurryModule as Module
from .objects.terms import Term, Symbol, DataType, Char, Var, Anonymous, anonymous, Reference
from .typecheck.errors import ConversionError, MismatchError, ArityError
from .typecheck.defaulting import DefaultingError

def info(module):
  return getattr(module, '.info')

def term(value, *, type=None):
  from .objects.terms import term as build_term
  return build_term(_interpreter_, value, type)

def parse(text, *, imports=()):
  from .objects.terms import parse as parse_term
  return parse_term(_interpreter_, text, imports)

def free(name=None, *, type=None, **legacy):
  from . import expressions as _expressions
  if legacy or isinstance(name, int):
    return _expressions.free(vid=legacy.pop('vid', 0 if name is None else name), **legacy)
  return Var(_interpreter_, name, type)

def choice(first, second, *more):
  from .objects.terms import choice as build_choice
  return build_choice(_interpreter_, first, second, *more)

def let(body, /, **bindings):
  from .objects.terms import let as build_let
  return build_let(_interpreter_, body, bindings)

def ref(name=None):
  from . import expressions as _expressions
  if name is None:
    return _expressions.ref()
  return Reference(_interpreter_, name)

def _qualified(name):
  parts = name.split('.')
  for index in range(len(parts) - 1, 0, -1):
    try:
      module = import_('.'.join(parts[:index]))
    except ModuleLookupError:
      continue
    return module, '.'.join(parts[index:])
  raise ModuleLookupError('no module prefix in %r' % name)

def symbol(name):
  module, local = _qualified(name)
  return module[local]
topython = _interpreter_.topython
def type(name):
  module, local = _qualified(name)
  try:
    return info(module).types[local]
  except KeyError:
    raise TypeLookupError('module %r has no type %r' % (module.__name__, local)) from None
def typeof(value, defaulted=False):
  if isinstance(value, str):
    value = term(value)
  return _interpreter_.typeof(value, defaulted=defaulted)

def getInterpreter():
  '''Get the global interpreter instance.'''
  return _interpreter_

def reload(flags={}):
  '''
  Hard-resets the interpreter.  Any flags supplied will be forwarded to the
  constructor, overriding flags supplied via the environment variable
  SPRITE_INTERPRETER_FLAGS.
  '''
  interpreter.reload(__name__, flags)


class ShowValue(object):
  @_visitation.dispatch.on('value')
  def __call__(self, value):
    return str(value)

  @__call__.when(tuple)
  def __call__(self, value):
    if len(value) == 1:
      return self(value[0])
    else:
      return '(%s)' % ','.join(map(self, value))

  @__call__.when(list)
  def __call__(self, value):
    return '[%s]' % ','.join(map(self, value))

  @__call__.when(_collections_abc.Sequence, no=str)
  def __call__(self, value):
    return self(list(value))

  @__call__.when(str)
  def __call__(self, value):
    # We need to add a single quote to the string to trick Python into
    # surrounding it with double quotes.
    value = repr(value + "'")
    value = value[:-2] + value[-1]
    return value

  @__call__.when(_collections_abc.Mapping)
  def __call__(self, value):
    return {self(k): self(v) for k,v in value.items()}


def show_value(value):
  '''
  Converts a Python Curry value to a string in Curry format.  This does a few
  things, such as lowering one-tuples; adjusting containers, such as tuples and
  lists, to print elements as with ``str`` rather than ``repr``; and converting
  free variable to friendly names _a, _b, etc.  The output should match other
  Curry systems.
  '''
  return ShowValue()(value)

__all__ += ['Term', 'Symbol', 'DataType', 'Module', 'Char', 'term', 'info', 'ConversionError', 'MismatchError', 'ArityError']

__all__ += ['parse', 'Var', 'Anonymous', 'anonymous', 'let']

__all__ += ['DefaultingError']

from .objects.results import Results, Answer, Bindings
# Load the node printer before exporting the public function of that name.
from .show import show as _show_node

def show(value):
  if isinstance(value, (Answer, Bindings)):
    return str(value)
  from .objects.termshow import show as show_term
  return show_term(value)

__all__ += ['solve', 'Results', 'Answer', 'Bindings', 'show', 'NoValueError', 'ManyValuesError', 'StaleError']
