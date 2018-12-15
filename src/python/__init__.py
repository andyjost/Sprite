'''
An interactive Curry environment.

This module creates a global instance of ``curry.interpreter.Interpreter`` and
provides an API to interact with it.

To perform a soft reset call ``reset``.  To change the interpreter flags, a
hard reset is required.  To perform a hard reset reload this module or call
``reload``.  The flags are read from the environment variable
SPRITE_INTERPRETER_FLAGS.  The ``reload`` function accepts arguments that
override.
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

