# The rotation of the C++ backend in step mode for every test file, however
# it is run (the runner and the CI script set the same default): the exact
# counters and the order of the values of a search then reproduce.  A value
# in the environment wins, so SPRITE_ROTATION=time:10ms runs a file in time
# mode; an empty value counts as unset, as it does for the interpreter.  The
# variable must be set before the first import of curry.
import os
if not os.environ.get('SPRITE_ROTATION'):
  os.environ['SPRITE_ROTATION'] = 'steps:65536'
# The warnings of the Curry front end (overlapping rules) off for every test
# file, as the runner and the benchmark harness set it, so the output of a
# suite does not change with the state of the products; a test of the
# warnings sets the variable itself (curry.toolchain._frontend).
if not os.environ.get('SPRITE_FRONTEND_WARNINGS'):
  os.environ['SPRITE_FRONTEND_WARNINGS'] = '0'
# The product cache of the C++ backend under tests/.cache, as the runner
# sets it, so a file run by hand writes nothing under the cache directory of
# the user.  A value in the environment wins; the empty string turns the
# cache off.
os.environ.setdefault(
    'SPRITE_PRODUCT_CACHE'
  , os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
      , '.cache', 'products'
      )
  )

from .checkers import check_expressions, check_indexing, check_predicate
import builtins
import contextlib
import functools
import gc
import os
import signal
import subprocess
import sys
import unittest

@contextlib.contextmanager
def trap():
  '''
  (Built-in) Traps test failures for debugging.

      with trap():
        self.assertTrue(...)
  '''
  try:
    yield None
  except Exception as e:
    breakpoint(msg=repr(str(e)), depth=2)
    raise

builtins.trap = trap

# Enable a break when certain exceptions occur.  For instance, this can be used
# to break whenever a RuntimeError or AssertionError occurs (n.b., that's an
# assertion failure, NOT a unittest.assert* failure).
def breakOn(exc_name):
  exception = getattr(builtins, exc_name)
  def __new__(cls, *args, **kwds):
    # breakpoint(depth=1)
    pdbtrace()
    return exception(*args, **kwds)
  replacement = type(exc_name, (exception,), {'__new__': __new__})
  setattr(builtins, exc_name, replacement)

  if exc_name:
    breakOn(exc_name)

# ================================================================================
# It is now OK to load the curry module.

from .testcase import TestCase, FunctionalTestCase
from io import StringIO
import importlib



def setio(stdin=None, stdout=None, stderr=None):
  '''
  Builds a decorator that configures the I/O of the global interpreter found in
  ``curry`` module.

  Note that TestCase resets the curry module after each test, so the I/O
  configuration is only affected for the test decorated.

  Parameters:
  -----------
    ``stdin``
        The configuration for stdin.  This can be a stream-like object (such as
        an open file) or a string.  If a string is provided, then it will be
        the input to the program.
    ``stdout``
        The configuration for stdout.  A stream-like object or string.  If a string
        is provided, then the output will be a StringIO object initialized with the
        given value.
    ``stderr``
        The configuration for stderr.  Similar to stdout.
  '''
  def setio(f):
    @functools.wraps(f)
    def wrapper(*args, **kwds):
      import curry
      interp = curry.getInterpreter()
      if stdin is not None:
        if isinstance(stdin, str):
          io = StringIO()
          io.write(stdin)
          io.seek(0)
          interp.stdin = io
        else:
          interp.stdin = stdin
      if stdout is not None:
        if isinstance(stdout, str):
          io = StringIO()
          io.write(stdout)
          interp.stdout = io
        else:
          interp.stdout = stdout
      if stderr is not None:
        if isinstance(stderr, str):
          io = StringIO()
          io.write(stderr)
          interp.stderr = io
        else:
          interp.stderr = stderr
      return f(*args, **kwds)
    return wrapper
  return setio


def with_flags(**flags):
  '''Test decorator that set the specified flags.  Implies hardreset.'''
  def decorator(f):
    @functools.wraps(f)
    @hardreset
    def replacement(*args, **kwds):
      import curry
      curry.reload(flags)
      return f(*args, **kwds)
    return replacement
  return decorator

def hardreset(f):
  '''Test decorator that hard-resets the curry module after the test runs.'''
  @functools.wraps(f)
  def decorator(*args, **kwds):
    try:
      return f(*args, **kwds)
    finally:
      import curry
      importlib.reload(curry)
      gc.collect() # The old interpreter is garbage.  Unload its modules now.
  return decorator

def readfile(filename, mode='r', fopen=open):
  with fopen(filename, mode) as istream:
    return istream.read()

class TimeoutError(AssertionError):
  '''
  Raised by ``timeout`` when a test exceeds its time limit.  An
  AssertionError, so the test fails rather than errors.
  '''

class timeout(contextlib.ContextDecorator):
  '''
  Fails a test that runs longer than ``seconds``.  Use it as a decorator or as
  a context manager::

      @cytest.timeout(10)
      def test_something(self):
        ...

      with cytest.timeout(10):
        ...

  The limit is enforced with SIGALRM, so it applies to Python code in the main
  thread.  Code that spins inside C++ is not interrupted; run such a test in a
  subprocess instead.  After the limit, the timer repeats every second in case
  the first exception is swallowed.

  Apply the decorator innermost, directly on the test function and below
  ``with_flags`` or ``hardreset``.  Their cleanup reloads ``curry``, and the
  repeating alarm must not fire inside it.
  '''
  def __init__(self, seconds):
    self.seconds = seconds

  def _expire(self, signum, frame):
    raise TimeoutError('timeout after %s seconds' % self.seconds)

  def __enter__(self):
    self.prev_handler = signal.signal(signal.SIGALRM, self._expire)
    signal.setitimer(signal.ITIMER_REAL, self.seconds, 1)
    return self

  def __exit__(self, *exc_info):
    signal.setitimer(signal.ITIMER_REAL, 0)
    signal.signal(signal.SIGALRM, self.prev_handler)
    return False

# The exit status of the ``timeout`` command when the time limit expires.
TIMEOUT_STATUS = 124

# True when the collector of the C++ backend runs at every safepoint
# (SPRITE_GC_STRESS=1; see src/cyrt/graph/gc/wdgc.cpp and section 4 of
# README).  A test whose child grows a large live heap, recurses deeply, or
# must run out of memory does not end in reasonable time in that mode.
GC_STRESS = os.environ.get('SPRITE_GC_STRESS') == '1'

def skipIfGcStress(reason):
  '''Skips a test when the collector runs in stress mode.'''
  return unittest.skipIf(GC_STRESS, 'collector stress mode: ' + reason)

def expectedFailureIf(condition, reason):
  '''
  Marks a test as a known failure when ``condition`` holds, and leaves it
  alone otherwise.  ``reason`` names the defect for the reader; unittest
  reports an expected failure without one.  Use it where a test runs on
  both backends and one of them has a known defect: the test keeps running
  there, and a fix shows as an unexpected success.
  '''
  if condition:
    return unittest.expectedFailure
  return lambda f: f

def interpret_mode():
  '''
  The value of the interpreter flag ``interpret`` of this session on the C++
  backend, or None on the Python backend, which ignores the flag.
  '''
  import curry
  if curry.flags['backend'] != 'cxx':
    return None
  return curry.flags['interpret']

def skipIfInterpreted(reason):
  '''
  Skips a test under the interpreter flag ``interpret`` set to 'new' or 'all'
  on the C++ backend.  A module loaded in those modes has no compiled object,
  and the test reads one.  Under 'tiered' the object exists once the prepare
  pass of the runner compiled the corpus (section 4 of README).
  '''
  mode = interpret_mode()
  return unittest.skipIf(
      mode in ('new', 'all'), 'interpret:%s: %s' % (mode, reason)
    )

def gc_backend():
  '''
  The collector of the installed C++ runtime: 'wdgc' or 'mps' (make GC=mps).
  See config.cxx_gc.
  '''
  from curry import config
  return config.cxx_gc()

def skipUnlessGcBackend(name, reason):
  '''
  Skips a test unless the installed C++ runtime uses the collector ``name``.
  The tests of the block heap and of its collector hold for 'wdgc' alone.
  '''
  return unittest.skipUnless(
      gc_backend() == name, 'collector %s only: %s' % (name, reason)
    )

def json_module(name, value):
  '''
  The ICurry-JSON of a module ``name`` with one public function, ``goal``,
  that returns the integer ``value``.  A toolchain test writes it to a
  ``.json.z`` file of its own and builds from there, so no Curry front end
  runs.  ``name`` may be dotted; the module then lives in a package.
  '''
  return (
      '{"__class__":"IProg","name":"%(name)s","imports":["Prelude"],"types":[]'
      ',"functions":[{"__class__":"IFunction","name":"%(name)s.goal","arity":0'
      ',"vis":{"__class__":"Public"},"needed":[],"body":{"__class__":'
      '"IFuncBody","block":{"__class__":"IBlock","vardecls":[],"assigns":[]'
      ',"stmt":'
      '{"__class__":"IReturn","expr":{"__class__":"ILit","lit":{"__class__":'
      '"IInt","value":%(value)d}}}}}}],"aliases":[]}'
    ) % {'name': name, 'value': value}

def run_in_subprocess(code, timeout, address_space=None, input=None, text=True):
  '''
  Runs Python ``code`` in a fresh interpreter and returns the
  ``subprocess.CompletedProcess`` with the text of both output streams, or
  their bytes when ``text`` is false.  ``input`` feeds the standard input of
  the child; by default the child inherits it.

  The child runs under the ``timeout`` command, which kills it after
  ``timeout`` seconds (exit status TIMEOUT_STATUS).  ``address_space`` caps
  its virtual memory in bytes through ``prlimit``.  The child inherits the
  environment and the working directory, so SPRITE_INTERPRETER_FLAGS selects
  the backend and CURRYPATH finds the test modules.  PYTHONIOENCODING is set
  to UTF-8, so the standard streams of a Python-backend child hold UTF-8 under
  any locale, as those of a C++-backend child do.

  Use this for a test that could spin or crash inside C++ on a regression.
  SIGALRM does not interrupt the C++ scheduler, so the ``timeout`` context
  manager cannot stop such a test, and a crash would end the test runner.
  '''
  cmd = ['timeout', str(timeout)]
  if address_space is not None:
    cmd = ['prlimit', '--as=%d' % address_space] + cmd
  cmd += [sys.executable, '-B', '-c', code]
  kwds = {} if input is None else {'input': input}
  env = dict(os.environ, PYTHONIOENCODING='utf-8')
  return subprocess.run(cmd, capture_output=True, text=text, env=env, **kwds)

