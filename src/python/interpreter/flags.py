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
    PDB.  The C++ backend compiles the modules it builds in the debug flavor
    (-O0 -g, assertions on) and keeps the objects the installation holds.  A
    session without the flag compiles the debug objects again, once.  See
    curry.backends.cxx.toolchain.

  * ``defaultconverter`` ('topython' | **None**)

    Indicates how to convert Curry results when returning to Python.
    With no conversion a list value, for example, is returned as a Curry
    list.  The 'topython' converter converts lists, tuples, strings,
    numbers, and other basic objects to their Python equivalents.

  * ``trace`` (True | **False**)

    Trace computations.

  * ``interpret`` (**'off'** | 'new' | 'all')

    How the C++ backend runs a module whose code is not compiled.  With
    'off', the toolchain compiles every module with the C++ compiler.  With
    'new', a module without a compiled object (a module compiled from a
    string, an expression, a source file compiled for the first time) is
    interpreted by the ICurry interpreter of the runtime (cyrt/icurry.hpp)
    instead, and a module with a current object is loaded from it.  With
    'all', every module is interpreted, the Prelude included; the compiled
    objects are not used.  The interpreter takes the same steps as compiled
    code on the same runtime; it runs a few times slower, and it starts at
    once.  The Python backend ignores this flag.

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

  * ``stack_limit`` (**4194304** | <int> | None)

    The number of bytes of C stack the C++ backend lets one evaluation use.
    When a nested evaluation reaches the limit, the backend unwinds to the
    scheduler and rotates the work queue.  So a deep alternative cannot crash
    the process or starve the others.  An alternative that cannot proceed
    within the limit is dropped.  Its error is reported after the other
    alternatives have run.  None disables the guard.  A limit larger than the
    stack of the thread is clamped to that stack, less a margin of 1 MiB.
    The Python backend ignores this flag.

  * ``step_budget`` (**2048** | <int> | None)

    The number of rewrite steps the Python backend gives one configuration
    before it rotates the work queue.  Rotation occurs only when another
    configuration waits in the same queue or in an enclosing one.  So a
    diverging alternative cannot starve the others, also not from inside a
    set function.  An alternative that overflows the Python stack runs again
    after the others.  When it overflows again without a step of progress,
    it is dropped, and its RecursionError is reported after the other
    alternatives have run.  None disables the step-budget rotation.  Rotation
    on residuation and on Python stack overflow still occurs.  The C++
    backend rotates after every 65536 forward nodes it compresses (about one
    per rewrite step) and ignores this flag.

  * ``telemetry_interval`` (**None** | <number>)

    Specifies the number of seconds between event reports in the log output.
    Events provide information about the state of the runtime system, such as
    the number of nodes created or steps performed.  If None or non-positive,
    this information is not reported.

  * ``typed_expr`` (**True** | False)

    Whether ``curry.expr`` types the expression it builds: the type schemes
    of the symbols are unified, Python values convert by the expected type,
    the class dictionaries are supplied, and a typing failure is an error
    at construction (see curry.typecheck.builder).  With False,
    ``curry.expr`` is the untyped builder of ``curry.raw_expr`` with the
    free and choice markers as calls of Prelude.unknown and Prelude.?, and
    the keyword exprtype is ignored.  The flag serves bisection and the
    performance program.
'''.format(config.default_backend())

FLAG_INFO = {
  #  Flag                   Value Spec           Default
  #  --------------------   -------------------  ----------------------------
    'backend'             : ({'cxx', 'py'}, config.default_backend())
  , 'debug'               : ( bool                , False )
  , 'defaultconverter'    : ({'topython', None}   , None  )
  , 'interpret'           : ({'off', 'new', 'all'}, 'off' )
  , 'trace'               : ( bool                , False )
  , 'keep_temp_files'     : ((bool, str)          , False )
  , 'lazycompile'         : ( bool                , True  )
  , 'postmortem'          : ( bool                , False )
  , 'setfunction_strategy': ({'eager', 'lazy'}    , 'lazy')
  , 'stack_limit'         : ({None, int}          , 4194304)
  , 'step_budget'         : ({None, int}          , 2048  )
  , 'telemetry_interval'  : ({None, float}        , None  )
  , 'typed_expr'          : ( bool                , True  )
  }

def get_default_flags():
  '''Returns the default flag values.'''
  return {flag: default for flag,(_,default) in FLAG_INFO.items()}

def _show(valspec): # pragma no cover
  if isinstance(valspec, str):
    return repr(valspec)
  if isinstance(valspec, set):
    valspec = sorted(valspec, key=repr)
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
  elif valspec is None:
    return repr(None)
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
    try:
      return int(given)
    except ValueError:
      pass
  elif valspec is float:
    try:
      return float(given)
    except ValueError:
      pass
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
    logger.warning('unknown flag: %r', flag)
    return NotImplemented
  else:
    valspec, default = FLAG_INFO[flag]
    converted = _convert(given, valspec)
    if converted is NotImplemented:
      logger.warning('cannot convert %r to a value for flag %r', given, flag)
      logger.warning('the prior value %r will be used'
        , str(currentflags.get(flag, default)))
      logger.warning('note: expected %s', _show(valspec))
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
