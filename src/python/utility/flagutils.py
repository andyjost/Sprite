'''
Utilities for working with interpreter flags.

The curry module provides a global interpreter instance whose flags are
controlled by the environment variable SPRITE_INTERPRETER_FLAGS.  Only this
interpreter is affected by the environment.  This module contains functions for
working with the flags that come from the environment.
'''
from .binding import binding
from .. import config
from ..utility import formatDocstring
import __builtin__, logging, os, sys

logger = logging.getLogger(__name__)

FLAG_INFO = {
  #  Flag                   Value Spec           Default
  #  --------------------   -------------------  -------------------------
    'backend'             : ({'py'}            , config.default_backend())
  , 'debug'               : ( bool             , False )
  , 'defaultconverter'    : ({'topython', None}, None  )
  , 'trace'               : ( bool             , False )
  , 'keep_temp_files'     : ((bool, str)       , False )
  , 'lazycompile'         : ( bool             , True  )
  , 'setfunction_strategy': ({'eager', 'lazy'} , 'lazy')
  , 'telemetry_interval'  : ({None, float}     , None  )
  }

def get_default_flags():
  return {flag: default for flag,(_,default) in FLAG_INFO.items()}

def show(valspec): # pragma no cover
  if isinstance(valspec, str):
    return repr(valspec)
  if isinstance(valspec, set):
    valspec = sorted(valspec)
    if len(valspec) == 1:
      return repr(list(valspec).pop())
    else:
      return '%s or %s' % (
          ', '.join(map(show, valspec[:-1]))
        , show(valspec[-1])
        )
  elif isinstance(valspec, tuple):
    if len(valspec) == 1:
      return repr(valspec[0])
    else:
      return '%s or %s' % (
          ', '.join(map(show, valspec[:-1]))
        , show(valspec[-1])
        )
  elif valspec is bool:
    return 'a Boolean'
  elif valspec is str:
    return 'a string'
  elif valspec is int:
    return 'an integer'
  elif valspec is float:
    return 'a number'
  assert False

def convert(given, valspec): # pragma no cover
  if isinstance(valspec, set):
    xs = [x for x in [convert(given, tgt) for tgt in valspec]
            if x is not NotImplemented]
    if len(xs) == 1:
      return xs.pop()
  elif isinstance(valspec, str):
    if valspec.startswith(given):
      return valspec
  elif valspec is str:
    return given
  elif valspec is int:
    return int(given)
  elif valspec is float:
    return float(given)
  elif valspec is bool:
    if any(s.startswith(given.lower())
           for s in ['true', 'on', 'yes', 'enable']):
      return True
    elif any(s.startswith(given.lower())
             for s in ['false', 'off', 'no', 'disable']):
      return False
    else:
      try:
        x = int(given)
      except ValueError:
        pass
      else:
        return bool(x)
  elif valspec is None:
    if any(s.startswith(given.lower())
           for s in ['none', 'nothing', 'default', 'off']):
      return None
  elif isinstance(valspec, tuple):
    for t in valspec:
      v = convert(given, t)
      if v is not NotImplemented:
        return v
  return NotImplemented

def flagval(flag, given, currentflags): # pragma: no cover
  if flag not in FLAG_INFO:
    logger.warn('unknown flag: %r', flag)
    return NotImplemented
  else:
    valspec, default = FLAG_INFO[flag]
    converted = convert(given, valspec)
    if converted is NotImplemented:
      logger.warn('cannot convert %r to a value for flag %r', given, flag)
      logger.warn('the prior value %r will be used'
        , str(currentflags.get(flag, default)))
      logger.warn('note: expected %s', show(valspec))
    return converted

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
        flag: converted for e in envflags.split(',')
                        for flag, given in [e.split(':')]
                        for converted in [flagval(flag, given, flags_out)]
                        if converted is not NotImplemented
      })
  flags_out.update(flags)
  return flags_out

@formatDocstring(__package__[:__package__.find('.')])
def reload(name, flags={}):
  '''Hard-resets the interpreter found in module "{}".'''
  flags = getflags(flags)
  envflags = ','.join('%s:%s' % (str(k), str(v)) for k,v in flags.items())
  with binding(os.environ, 'SPRITE_INTERPRETER_FLAGS', envflags):
    this = sys.modules[name]
    __builtin__.reload(this)

