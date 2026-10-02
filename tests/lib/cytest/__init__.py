from .checkers import check_expressions, check_indexing, check_predicate
import builtins
import contextlib
import functools
import gc
import os
import signal
import subprocess
import sys

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

def run_in_subprocess(code, timeout, address_space=None):
  '''
  Runs Python ``code`` in a fresh interpreter and returns the
  ``subprocess.CompletedProcess`` with the text of both output streams.

  The child runs under the ``timeout`` command, which kills it after
  ``timeout`` seconds (exit status TIMEOUT_STATUS).  ``address_space`` caps
  its virtual memory in bytes through ``prlimit``.  The child inherits the
  environment and the working directory, so SPRITE_INTERPRETER_FLAGS selects
  the backend and CURRYPATH finds the test modules.

  Use this for a test that could spin or crash inside C++ on a regression.
  SIGALRM does not interrupt the C++ scheduler, so the ``timeout`` context
  manager cannot stop such a test, and a crash would end the test runner.
  '''
  cmd = ['timeout', str(timeout)]
  if address_space is not None:
    cmd = ['prlimit', '--as=%d' % address_space] + cmd
  cmd += [sys.executable, '-B', '-c', code]
  return subprocess.run(cmd, capture_output=True, text=True)

