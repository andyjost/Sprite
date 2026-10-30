from .. import config
from ..exceptions import FlagError
import logging, os, sys

logger = logging.getLogger(__name__)

__doc__ =\
'''
Defines the flags used to configure a Curry interpreter.

The flags of an interpreter start from the environment.  The base is the
defaults below; SPRITE_ROTATION sets the flag ``rotation`` over them;
SPRITE_INTERPRETER_FLAGS sets any flag over that; and the argument of
``Interpreter(flags=...)`` or of ``curry.reset(**flags)`` wins (see getflags).
So an interpreter built directly runs as the process does, on the backend
and in the mode of the environment, unless its argument says otherwise.

The following flags are available:

  * ``backend`` (**'cxx'**)

    The runtime used to compile and run Curry.  Its only value is 'cxx'.

  * ``checker`` (True | **False**)

    The checker mode of the Fair Scheme proofs program (section 6.5 of the
    memo on the Fair Scheme proofs).  The runtime holds a checker while
    the flag is on (curryrt/checker.hpp, RuntimeState::checker).  The
    checker asserts the run-time invariants of the Fair Scheme at every
    fork, escape, pull-tab, instantiation and yield: the identifier
    consistency of the fingerprints and their groups (RI B1), the
    generators of the free variables and the reducts of the configurations
    across a write of a generator and a private copy of the spine (X1,
    X-b, X-b', X-c), the two groups of the choices inside a set function
    and the split of its queue (S0, S-split), and the inductive positions
    and the failures of every step against the definitional tree of its
    operation (B2; the C++ runtime reads the tree from the bytecode of an
    interpreted operation, so a compiled operation is not checked there).
    A violation raises ``InvariantViolation``, an ``AssertionError`` whose
    message names the invariant, the event, the configuration, the
    identifiers and the goal position; the C++ backend raises
    ``curry.backends.cxx.curryrtbindings.InvariantViolation``.  The checker
    observes: it changes no step, no value and no counter, and with the
    flag off each runtime tests one attribute or one pointer per event.
    The developer notes describe the checker.

  * ``debug`` (True | **False**)

    Sacrifice speed to add more consistency checks and enable debugging with
    gdb.  The C++ backend compiles the modules it builds in the debug flavor
    (-O0 -g, assertions on) and keeps the objects the installation holds.  A
    session without the flag compiles the debug objects again, once.  See
    curry.backends.cxx.toolchain.

  * ``trace`` (True | **False**)

    Reserved for compatibility.  Runtime traces require a TRACE build.

  * ``jit`` (**'off'** | 'eager' | 'hot')

    The JIT of the C++ backend (curry.backends.cxx.llvmjit; issue #65),
    under the modes 'new' and 'all' of ``interpret``.  With 'eager', every
    function of a module is compiled to machine code through LLVM when the
    module is loaded; with 'hot', a thread of the process compiles the
    functions that reach SPRITE_JIT_THRESHOLD calls (100 by default) while
    the evaluation runs, and the scheduler swaps their steps at its
    safepoint.  The JIT needs the extra ``curry[jit]`` (llvmlite) and the
    bitcode of the helpers of the runtime, which the build makes when
    CMake finds clang (WITH_CLANG); without them the functions stay
    interpreted and the reason is logged once.  Under 'tiered' the
    background compile swaps the steps itself, so the flag has no effect
    there, nor under 'off'.

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
    'off', the toolchain compiles every module with the C++ compiler.  A
    module imported from an ICurry object (``curry.import_(imodule)``),
    which the toolchain never sees, is compiled at its first use: the first
    call of one of its functions generates the C++ of the ICurry object,
    compiles it as ``sprite-make --so`` would, and swaps the functions of
    the module to the compiled code (curry.backends.cxx.materialize).  When
    the object is the translation of the source on disk, the products go
    beside the source and into the product cache, and a current object
    there is adopted without a compile; an object changed in memory, or
    without a source file, compiles into a directory of the process.  A
    function without code that is called all the same, because the compile
    failed or because the hook
    ``curry.backends.cxx.materialize.COMPILE_ON_FIRST_USE`` is False (the
    tests use it), raises ``EvaluationError`` that names the function, its
    module and the reason (issue #102).  With
    'new', a module without a compiled object (a module compiled from a
    string, an expression, a source file compiled for the first time) is
    interpreted by the ICurry interpreter of the runtime (curryrt/icurry.hpp)
    instead, and a module with a current object is loaded from it.  With
    'all', every module is interpreted, the Prelude included; the compiled
    objects are not used; it is the default on Windows, where the compile of
    generated code is not available in this release.  With 'tiered', the
    default on the other platforms, a
    module without a compiled object is interpreted at once, as under
    'new', a child process compiles it in the background, and the runtime
    swaps the functions of the module to the compiled code when the object
    is ready, during a running evaluation included (see
    curry.backends.cxx.tiered): the load of the object binds its slots to
    the tables the interpreter made (the binding in curryrt/dynload.hpp;
    issue #163).  An expression, an interactive module, and a module
    compiled from a string stay interpreted.  The interpreter takes the
    same steps as compiled code on the same runtime; it runs a few times
    slower, and it starts at once.

  * ``keep_temp_files``  (True | **False** | <str>)

    Keep temporary files and directories.  If a nonempty string is supplied,
    then it is treated as a directory name and all temporary files will be
    written there.

  * ``lazycompile``

    Reserved for compatibility; this flag has no effect.

  * ``postmortem`` (True | **False**)

    When compiling a string of Curry code fails, copy the generated code to the
    current working directory for post-mortem analysis.

  * ``recursion_limit``

    Reserved for compatibility; this flag has no effect.

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
    CI jobs set ``steps:65536`` through it.

  * ``stack_limit`` (**4194304** | <int> | None)

    The number of bytes of C stack the C++ backend lets one evaluation use.
    When a nested evaluation reaches the limit, the backend unwinds to the
    scheduler and rotates the work queue.  So a deep alternative cannot crash
    the process or starve the others.  When a retry makes no progress,
    evaluation escalates to the heap's worker (see ``worker_stack``).  If
    escalation is disabled or the worker exhausts its stack too, the
    alternative is dropped and its error follows the other values.  None
    disables the guard.  A limit larger than the stack of the thread is clamped to that stack, less a margin of 1 MiB.

  * ``worker_stack`` (**1073741824** | <int> | None)

    The stack reservation in bytes of the C++ backend's retained worker.
    Evaluation starts on the caller's thread; a stalled stack unwind moves
    it to this worker.  The default reserves 1 GiB of virtual address space;
    pages become resident when touched.  A refused reservation is halved
    down to 64 MiB.  If every attempt fails, StackLimitError names the sizes.
    None disables escalation.  The worker is shared by evaluations of the
    heap and stays alive after use; a changed size replaces the idle worker.

  * ``step_budget``

    Reserved for compatibility; this flag has no effect.

  * ``telemetry_interval`` (**None** | <number>)

    Reserved for compatibility; this flag has no effect.  Use curry.stats
    or sprite-exec --stats for runtime counters.


'''

FLAG_INFO = {
  #  Flag                   Value Spec           Default
  #  --------------------   -------------------  ----------------------------
    'backend'             : ({'cxx'}, 'cxx')
  , 'checker'             : ( bool                , False )
  , 'debug'               : ( bool                , False )
  , 'inline_budget'       : ( int                 , 4     )
  , 'interpret'           : ({'off', 'new', 'all', 'tiered'}, 'all' if sys.platform == 'win32' else 'tiered')
  , 'jit'                 : ({'off', 'eager', 'hot'}, 'off')
  , 'trace'               : ( bool                , False )
  , 'keep_temp_files'     : ((bool, str)          , False )
  , 'lazycompile'         : ( bool                , True  )
  , 'postmortem'          : ( bool                , False )
  , 'recursion_limit'     : ({None, int}          , 1 << 18)
  , 'rotation'            : ( str                 , 'time:10ms')
  , 'stack_limit'         : ({None, int}          , 4194304)
  , 'worker_stack'        : ({None, int}          , 1 << 30)
  , 'step_budget'         : ({None, int}          , 2048  )
  , 'telemetry_interval'  : ({None, float}        , None  )
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
  """Validate session flags, including values supplied directly by Python."""
  for flag, value in flags.items():
    if flag not in FLAG_INFO:
      raise FlagError('%r is not a flag; the flags are %s' %
          (flag, ', '.join(FLAG_INFO)))
    spec = FLAG_INFO[flag][0]
    choices = spec if isinstance(spec, (set, tuple)) else (spec,)
    valid = any(type(value) is choice if isinstance(choice, type)
        else type(value) is type(choice) and value == choice for choice in choices)
    if not valid:
      raise FlagError('%r is not a value for flag %r; expected %s' %
          (value, flag, _show(spec)))
    if flag == 'rotation':
      try:
        parse_rotation(value)
      except ValueError as error:
        raise FlagError(str(error)) from None


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
  if envflags:
    for item in envflags.split(','):
      flag, colon, given = item.partition(':')
      if not colon:
        raise FlagError('%r is not a flag setting; expected name:value' % item)
      check_flags({flag: FLAG_INFO[flag][1]} if flag in FLAG_INFO else {flag: None})
      converted = _convert(given, FLAG_INFO[flag][0])
      if converted is NotImplemented:
        raise FlagError('%r is not a value for flag %r; expected %s' %
            (given, flag, _show(FLAG_INFO[flag][0])))
      flags_out[flag] = converted
  flags_out.update(flags)
  check_flags(flags_out)
  return flags_out
