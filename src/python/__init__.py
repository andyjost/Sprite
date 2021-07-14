'''
The Sprite Curry system.

This package contains everything one needs to compile and execute Curry code.
The topmost module provides an instance of the Curry system and an API to
interact with it.

To perform a soft reset call ``reset``.  This returns the system to its
original state, with no definitions and no modules imported.  The configuration
is taken from environment variable SPRITE_INTERPRETER_FLAGS.  To change that at
runtime, use the ``reload`` function while specifying new flags.

Use ``import_`` to import Curry modules, ``compile`` to compile Curry code,
``expr`` to build Curry expressions, and ``eval`` to evaluate them.  ``path``
determines where Sprite searches for Curry code.  Loaded modules can be found
under ``modules``.  Use ``topython`` to convert Curry values to Python objects.

*Example* ::

    >>> mymodule = curry.compile("""
    ... data Item = A | B
    ... rotate A = B
    ... rotate B = A
    ... main :: Item
    ... main = rotate A ? rotate B
    ... """)
    >>> for value in curry.eval(mymodule.main):
    ...   print value
    B
    A
'''

# Install breakpoint into __builtins__.
from .utility import breakpoint
del breakpoint

# Validate SPRITE_HOME.
import os
if 'SPRITE_HOME' not in os.environ:
  raise ImportError('SPRITE_HOME is not set in the environment')
if not os.path.isdir(os.environ['SPRITE_HOME']):
  raise ImportError('SPRITE_HOME is not a directory')
if not os.access(os.environ['SPRITE_HOME'], os.O_RDONLY):
  raise ImportError('SPRITE_HOME is not readable')
del os

from .exceptions import *
from . import interpreter
from .utility import flagutils as _flagutils
from .utility import visitation as _visitation
from .utility.unboxed import unboxed
import collections as _collections

_interpreter_ = interpreter.Interpreter(flags=_flagutils.getflags())

compile = _interpreter_.compile
currytype = _interpreter_.currytype
eval = _interpreter_.eval
expr = _interpreter_.expr
flags = _interpreter_.flags
import_ = _interpreter_.import_
module = _interpreter_.module
modules = _interpreter_.modules
path = _interpreter_.path
reset = _interpreter_.reset
symbol = _interpreter_.symbol
topython = _interpreter_.topython
type = _interpreter_.type

def getInterpreter():
  '''Get the global interpreter instance.'''
  return _interpreter_

def reload(flags={}):
  '''
  Hard-resets the interpreter.  Any flags supplied will be forwarded to the
  constructor, overriding flags supplied via the environment variable
  SPRITE_INTERPRETER_FLAGS.
  '''
  _flagutils.reload(__name__, flags)


class ShowValue(object):
  def __init__(self):
    from .interpreter import show
    self.stringify = show.ReplStringifier()

  @_visitation.dispatch.on('value')
  def __call__(self, value):
    return self.stringify(value)

  @__call__.when(tuple)
  def __call__(self, value):
    if len(value) == 1:
      return self(value[0])
    else:
      return '(%s)' % ','.join(map(self, value))

  @__call__.when(list)
  def __call__(self, value):
    return '[%s]' % ','.join(map(self, value))

  @__call__.when(_collections.Sequence, no=str)
  def __call__(self, value):
    return self(list(value))

  @__call__.when(str)
  def __call__(self, value):
    # We need to add a single quote to the string to trick Python into
    # surrounding it with double quotes.
    value = repr(value + "'")
    value = value[:-2] + value[-1]
    return value

  @__call__.when(_collections.Mapping)
  def __call__(self, value):
    return {self(k): self(v) for k,v in value.iteritems()}


def show_value(value):
  '''
  Converts a Python Curry value to a string in Curry format.  This does a few
  things, such as lowering one-tuples; adjusting containers, such as tuples and
  lists, to print elements as with ``str`` rather than ``repr``; and converting
  free variable to friendly names _a, _b, etc.  The output should match other
  Curry systems.
  '''
  return ShowValue()(value)
