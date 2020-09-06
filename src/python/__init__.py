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

Example:
--------
>>> mymodule = curry.compile("""
... data Item = A | B
... rotate A = B
... rotate B = A
... main :: Item
... main = rotate A ? rotate B
... """)
>>> list(curry.eval(mymodule.main))
[<B>, <A>]
'''

from . import interpreter
from .exceptions import *
from .utility.unboxed import unboxed
from .utility import flagutils as _flagutils

_interpreter_ = interpreter.Interpreter(
    flags=_flagutils.getflags(weakflags={'defaultconverter':'topython'})
  )

compile = _interpreter_.compile
currytype = _interpreter_.currytype
eval = _interpreter_.eval
expr = _interpreter_.expr
flags = _interpreter_.flags
import_ = _interpreter_.import_
module = _interpreter_.module
modules = _interpreter_.modules
path = _interpreter_.path
prelude = _interpreter_.prelude
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

