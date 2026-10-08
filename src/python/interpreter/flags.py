from .. import config
import logging, os, sys

logger = logging.getLogger(__name__)

__doc__ =\
'''
Defines the flags used to configure a Curry interpreter.

The flags of an interpreter start from the environment.  The base is the
defaults below; SPRITE_ROTATION sets the flag ``rotation`` over them;
SPRITE_INTERPRETER_FLAGS sets any flag over that; and the argument of
``Interpreter(flags=...)`` or of ``curry.reload(flags)`` wins (see getflags).
So an interpreter built directly runs as the process does, on the backend
and in the mode of the environment, unless its argument says otherwise.

The following flags are available:

  * ``backend`` ({0!r})

    The name of the backend used to compile and run Curry: 'cxx', the C++
    backend.  The default is the one configure recorded
    (--with-default-backend; sysconfig/default_backend of the
    installation).  The value 'py' selects the Python backend, the
    reference implementation kept behind this flag until its removal
    (issue #82); the developer notes of the documentation describe it.

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

  * ``inline_budget`` (**4** | <int>)

    The largest function body, in nodes built, that the optimizer inlines at
    a saturated call (curry.interpreter.optimize.inline_calls).  A call of a
    non-recursive function whose body is an expression of at most this many
    calls, constructors, choices, and literals is replaced by the body, with
    every argument expression built once (call-time choice).  The same pass
    replaces a call of a single-case function on a constructor argument by
    the branch of that constructor, up to a fixed limit of its own.  0 turns
    both rules off.  The compiled form of a module records the keys of the
    passes, not the budget, so a module compiled under one budget runs as it
    was compiled under another; the background compile of the tiered mode
    runs under the budget of the interpreter.  The flag serves bisection and
    the performance program.

  * ``interpret`` ('off' | 'new' | 'all' | **'tiered'**)

    How the C++ backend runs a module whose code is not compiled.  With
    'off', the toolchain compiles every module with the C++ compiler.  With
    'new', a module without a compiled object (a module compiled from a
    string, an expression, a source file compiled for the first time) is
    interpreted by the ICurry interpreter of the runtime (cyrt/icurry.hpp)
    instead, and a module with a current object is loaded from it.  With
    'all', every module is interpreted, the Prelude included; the compiled
    objects are not used.  With 'tiered', the default, a module without a
    compiled object is interpreted at once, as under 'new', a child process
    compiles it in the background, and the runtime swaps the functions of
    the module to the compiled code when the object is ready, during a
    running evaluation included (see curry.backends.cxx.tiered).  An
    expression, an interactive module, and a module compiled from a string
    stay interpreted.  The interpreter takes the same steps as compiled code
    on the same runtime; it runs a few times slower, and it starts at once.
    The Python backend ignores this flag.

  * ``keep_temp_files``  (True | **False** | <str>)

    Keep temporary files and directories.  If a nonempty string is supplied,
    then it is treated as a directory name and all temporary files will be
    written there.

  * ``lazycompile`` (**True** | False)

    Wait to materialize Functions until they are needed.

  * ``postmortem`` (True | **False**)

    When compiling a string of Curry code fails, copy the generated code to the
    current working directory for post-mortem analysis.

  * ``recursion_limit`` (**262144** | <int> | None)

    The number of Python frames the Python backend lets one value nest: the
    recursion limit of the interpreter while a value is computed.  The
    backend evaluates a nested step by a recursive Python call, about eight
    frames per element of a list under a function that is not tail
    recursive, such as ``length`` or ``sort``, so the default covers a list
    of about thirty thousand elements.  An alternative that reaches the
    limit is handled as under ``step_budget``: it runs again after the
    others and is dropped when it overflows again without progress.  A
    larger limit costs memory, about 4 KB per nested element.  None leaves
    the limit of the interpreter as it is.  The C++ backend ignores this
    flag; see ``stack_limit``.

  * ``rotation`` (**'time:10ms'** | 'time:<N>ms' | 'steps:<N>')

    How the C++ backend paces the rotation of its queue of alternatives.  The
    scheduler rotates at a safepoint, after a completed rewrite step, so a
    diverging alternative cannot starve the others.  In time mode
    (``time:10ms``, the default; the unit may be ``s``, ``ms``, ``us`` or
    ``ns``) a ticker thread sets one byte every quantum and the safepoint
    polls it: the latency of a waiting alternative is bounded by the quantum
    whatever a step costs.  In step mode (``steps:65536``) the safepoint
    counts the steps and rotates every N of them: the schedule depends on
    the program alone, so the exact steps and forks of a search, and the
    order of its values, reproduce between runs.  A deterministic
    subcomputation never rotates in either mode, because a queue of one
    configuration has nothing to rotate; but in time mode two runs of a
    non-deterministic goal may print their values in a different order.
    Time mode starts its thread at the first evaluation, so a host that
    forks after an evaluation is multi-threaded (Python warns on
    ``os.fork``); the forked child starts a ticker of its own at its first
    evaluation.  Step mode starts no thread.  The environment variable
    SPRITE_ROTATION sets the flag below SPRITE_INTERPRETER_FLAGS (an empty
    value counts as unset); the test runner, the benchmark harness and the
    CI jobs set ``steps:65536`` through it.  The Python backend keeps its
    ``step_budget`` and ignores this flag.

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
    backend paces its rotation with the flag ``rotation`` and ignores this
    flag.

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
  , 'inline_budget'       : ( int                 , 4     )
  , 'interpret'           : ({'off', 'new', 'all', 'tiered'}, 'tiered')
  , 'trace'               : ( bool                , False )
  , 'keep_temp_files'     : ((bool, str)          , False )
  , 'lazycompile'         : ( bool                , True  )
  , 'postmortem'          : ( bool                , False )
  , 'recursion_limit'     : ({None, int}          , 1 << 18)
  , 'rotation'            : ( str                 , 'time:10ms')
  , 'setfunction_strategy': ({'eager', 'lazy'}    , 'lazy')
  , 'stack_limit'         : ({None, int}          , 4194304)
  , 'step_budget'         : ({None, int}          , 2048  )
  , 'telemetry_interval'  : ({None, float}        , None  )
  , 'typed_expr'          : ( bool                , True  )
  }

def get_default_flags():
  '''Returns the default flag values.'''
  return {flag: default for flag,(_,default) in FLAG_INFO.items()}

# The units of the quantum of time mode, in nanoseconds.
_TIME_UNITS = {'s': 10**9, 'ms': 10**6, 'us': 10**3, 'ns': 1}

def parse_rotation(text):
  '''
  Parses a value of the flag ``rotation``: ``time:<N><unit>`` with a unit of
  s, ms, us or ns, or ``steps:<N>``.  Returns ``('time', nanoseconds)`` or
  ``('steps', count)``; both numbers are positive integers below 2**63, so
  that the runtime can hold them.  Raises ValueError for other text.
  '''
  error = ValueError(
      'bad rotation setting %r: expected time:<N>ms or steps:<N>' % (text,)
    )
  if not isinstance(text, str):
    raise error
  mode, _, value = text.strip().partition(':')
  mode, value = mode.strip(), value.strip()
  if mode == 'steps':
    if not value.isdigit() or not (1 <= int(value) < 2 ** 63):
      raise error
    return 'steps', int(value)
  if mode == 'time':
    for unit, scale in sorted(_TIME_UNITS.items(), key=lambda u: -len(u[0])):
      if value.endswith(unit):
        number = value[:-len(unit)].strip()
        try:
          quantum = float(number) * scale
        except ValueError:
          raise error from None
        # At least one nanosecond, finite, and within a 64-bit count.
        if not number or not (1 <= quantum < 2 ** 63):
          raise error
        return 'time', int(round(quantum))
  raise error

def check_flags(flags):
  '''
  Raises ValueError for a flag value that cannot be used: today the flag
  ``rotation``.  The other flags are checked when they are converted.
  '''
  if 'rotation' in flags:
    parse_rotation(flags['rotation'])

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
  Merges flags specified in the environment with those supplied.

  Reads flags from the environment variable SPRITE_INTERPRETER_FLAGS,
  interprets them as Python values, and then combines them with the ones
  supplied to this function.  The environment variable SPRITE_ROTATION sets
  the flag ``rotation`` alone; an empty value counts as unset.  The global
  interpreter, ``curry.reload`` and ``Interpreter(flags)`` all start from
  this merge, so every interpreter follows the environment of the process
  below the flags it was given.

  The precedence order is as follows:

      ``flags`` > SPRITE_INTERPRETER_FLAGS > SPRITE_ROTATION > ``weakflags``
      > defaults

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
  rotation = os.environ.get('SPRITE_ROTATION')
  if rotation:
    flags_out['rotation'] = rotation
  envflags = os.environ.get('SPRITE_INTERPRETER_FLAGS')
  if envflags: # pragma: no cover
    # A value may hold a colon of its own (rotation:time:10ms), so an item
    # splits at its first colon only.
    flags_out.update({
        flag: converted for e in envflags.split(',')
                        for flag, given in [e.split(':', 1)]
                        for converted in [_flagval(flag, given, flags_out)]
                        if converted is not NotImplemented
      })
  flags_out.update(flags)
  return flags_out
