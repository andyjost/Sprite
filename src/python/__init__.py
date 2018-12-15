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

def _flagval(v): # pragma: no cover
  '''Try to interpret the string ``v`` as a flag value.'''
  try:
    return {'True':True, 'False':False}[v]
  except KeyError:
    pass
  try:
    return int(v)
  except ValueError:
    pass
  return v

def _getflags(flags={}, weakflags={}):
  '''
  Reads interpreter flags from the environment variable
  SPRITE_INTERPRETER_FLAGS and then combines them with the ones supplied to
  this function.

  Those supplied via ``flags`` supercede ones found in the environment.  Those
  supplied via ``weakflags`` are superceded by ones found in the environment.
  '''
  import os
  flags_out = {}
  flags_out.update(weakflags)
  envflags = os.environ.get('SPRITE_INTERPRETER_FLAGS')
  if envflags: # pragma: no cover
    flags_out.update({
        k:_flagval(v) for e in envflags.split(',') for k,v in [e.split(':')]
      })
  flags_out.update(flags)
  return flags_out

_interpreter_ = interpreter.Interpreter(
    flags=_getflags(weakflags={'defaultconverter':'topython'})
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
  from .utility.binding import binding
  import __builtin__
  import os
  import sys
  flags = _getflags(flags)
  envflags = ','.join('%s:%s' % (str(k), str(v)) for k,v in flags.items())
  with binding(os.environ, 'SPRITE_INTERPRETER_FLAGS', envflags):
    this = sys.modules[__name__]
    __builtin__.reload(this)

