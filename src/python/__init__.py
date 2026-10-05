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
  _interpreter_._expression_modules = []
_interpreter_ = interpreter.Interpreter(flags=_flags.getflags())

compile = _interpreter_.compile
currytype = _interpreter_.currytype
describe = _interpreter_.describe
eval = _interpreter_.eval
expr = _interpreter_.expr
flags = _interpreter_.flags
'''
The ``flags`` attribute of the global interpreter.  Modify this to reconfigure
the interpreter.

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
variable CURRYPATH.  Modify this to dynamically adjust the Curry search path.

:meta hide-value:
'''

raw_expr = _interpreter_.raw_expr
reset = _interpreter_.reset
save = _interpreter_.save
stats = _interpreter_.stats
symbol = _interpreter_.symbol
topython = _interpreter_.topython
type = _interpreter_.type
typeof = _interpreter_.typeof

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
