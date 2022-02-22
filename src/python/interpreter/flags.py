from .. import config
import logging, os, sys

logger = logging.getLogger(__name__)

__doc__ =\
'''
Defines the flags used to configure a Curry interpreter.  The following flags
are available:

  * ``backend`` ({0!r})

    The name of the backend used to compile and run Curry.

  * ``debug`` (True | **False**)

    Sacrifice speed to add more consistency checks and enable debugging with
    PDB.

  * ``defaultconverter`` ('topython' | **None**)

    Indicates how to convert Curry results when returning to Python.
    With no conversion a list value, for example, is returned as a Curry
    list.  The 'topython' converter converts lists, tuples, strings,
    numbers, and other basic objects to their Python equivalents.

  * ``trace`` (True | **False**)

    Trace computations.

  * ``keep_temp_files``  (True | **False** | <str>)

    Keep temporary files and directories.  If a nonempty string is supplied,
    then it is treated as a directory name and all temporary files will be
    written there.

  * ``lazycompile`` (**True** | False)

    Wait to materialize Functions until they are needed.

  * ``postmortem`` (True | **False**)

    When compiling a string of Curry code fails, copy the generated code to the
    current working directory for post-mortem analysis.

  * ``setfunction_strategy`` (**'lazy'** | 'eager')

    Indicates how to evaluate set functions.  If 'lazy', then set guards are
    used (similar to KiCS2).  Otherwise, each argument is reduced to ground
    normal form before applying the set function (similar to PAKCS).

  * ``telemetry_interval`` (**None** | <number>)

    Specifies the number of seconds between event reports in the log output.
    Events provide information about the state of the runtime system, such as
    the number of nodes created or steps performed.  If None or non-positive,
    this information is not reported.
'''.format(config.default_backend())

FLAG_INFO = {
  #  Flag                   Value Spec           Default
  #  --------------------   -------------------  ----------------------------
    'backend'             : ({'cpp', 'llvm', 'py'}, config.default_backend())
  , 'debug'               : ( bool                , False )
  , 'defaultconverter'    : ({'topython', None}   , None  )
  , 'trace'               : ( bool                , False )
  , 'keep_temp_files'     : ((bool, str)          , False )
  , 'lazycompile'         : ( bool                , True  )
  , 'postmortem'          : ( bool                , False )
  , 'setfunction_strategy': ({'eager', 'lazy'}    , 'lazy')
  , 'telemetry_interval'  : ({None, float}        , None  )
  }

def get_default_flags():
  '''Returns the default flag values.'''
  return {flag: default for flag,(_,default) in FLAG_INFO.items()}

def _show(valspec): # pragma no cover
  if isinstance(valspec, str):
    return repr(valspec)
  if isinstance(valspec, set):
    valspec = sorted(valspec)
    if len(valspec) == 1:
      return repr(list(valspec).pop())
    else:
      return '%s or %s' % (
          ', '.join(map(_show, valspec[:-1]))
        , _show(valspec[-1])
        )
  elif isinstance(valspec, tuple):
    if len(valspec) == 1:
      return repr(valspec[0])
    else:
      return '%s or %s' % (
          ', '.join(map(_show, valspec[:-1]))
        , _show(valspec[-1])
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

def _convert(given, valspec): # pragma no cover
  if isinstance(valspec, set):
    xs = [x for x in [_convert(given, tgt) for tgt in valspec]
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
      v = _convert(given, t)
      if v is not NotImplemented:
        return v
  return NotImplemented

def _flagval(flag, given, currentflags): # pragma: no cover
  if flag not in FLAG_INFO:
    logger.warn('unknown flag: %r', flag)
    return NotImplemented
  else:
    valspec, default = FLAG_INFO[flag]
    converted = _convert(given, valspec)
    if converted is NotImplemented:
      logger.warn('cannot convert %r to a value for flag %r', given, flag)
      logger.warn('the prior value %r will be used'
        , str(currentflags.get(flag, default)))
      logger.warn('note: expected %s', _show(valspec))
    return converted

def getflags(flags={}, weakflags={}):
  '''
  Merges flags specified in the environement with those supplied.

  Reads flags from the environment variable SPRITE_INTERPRETER_FLAGS,
  interprets them as Python values, and then combines them with the ones
  supplied to this function.

  The precedence order is as follows:

      ``flags`` > SPRITE_INTERPRETER_FLAGS > ``weakflags`` > defaults

  Args:
    flags:
      A dict containing flag settings with the highest precedence.
    weakflags:
      A dict containing flag settings with the lowest precedence (aside from
      defaults).

  Returns:
    A dict containing the combined flag settings.
  '''
  flags_out = {}
  flags_out.update(weakflags)
  envflags = os.environ.get('SPRITE_INTERPRETER_FLAGS')
  if envflags: # pragma: no cover
    flags_out.update({
        flag: converted for e in envflags.split(',')
                        for flag, given in [e.split(':')]
                        for converted in [_flagval(flag, given, flags_out)]
                        if converted is not NotImplemented
      })
  flags_out.update(flags)
  return flags_out
