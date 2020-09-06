'''
Utilities for working with interpreter flags.

The curry module provides a global interpreter instance whose flags are
controlled by the environment variable SPRITE_INTERPRETER_FLAGS.  Only this
interpreter is affected by the environment.  This module contains functions for
working with the flags that come from the environment.
'''
from .binding import binding
from .. import utility
import __builtin__
import os
import sys

def flagval(v): # pragma: no cover
  '''Tries to interpret the string ``v`` as a flag value.'''
  try:
    return {'True':True, 'False':False}[v]
  except KeyError:
    pass
  try:
    return int(v)
  except ValueError:
    pass
  return v

def getflags(flags={}, weakflags={}):
  '''
  Reads interpreter flags from the environment variable
  SPRITE_INTERPRETER_FLAGS and then combines them with the ones supplied to
  this function.

  Those supplied via ``flags`` supercede ones found in the environment.  Those
  supplied via ``weakflags`` are superceded by ones found in the environment.
  '''
  flags_out = {}
  flags_out.update(weakflags)
  envflags = os.environ.get('SPRITE_INTERPRETER_FLAGS')
  if envflags: # pragma: no cover
    flags_out.update({
        k:flagval(v) for e in envflags.split(',') for k,v in [e.split(':')]
      })
  flags_out.update(flags)
  return flags_out

@utility.format_docstring(__package__[:__package__.find('.')])
def reload(name, flags={}):
  '''Hard-resets the interpreter found in module "{}".'''
  flags = getflags(flags)
  envflags = ','.join('%s:%s' % (str(k), str(v)) for k,v in flags.items())
  with binding(os.environ, 'SPRITE_INTERPRETER_FLAGS', envflags):
    this = sys.modules[name]
    __builtin__.reload(this)

