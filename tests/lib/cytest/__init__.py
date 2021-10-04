from cStringIO import StringIO
import contextlib
import functools
import __builtin__
from .checkers import check_expressions, check_indexing, check_predicate

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

__builtin__.trap = trap

# Enable a break when certain exceptions occur.  For instance, this can be used
# to break whenever a RuntimeError or AssertionError occurs (n.b., that's an
# assertion failure, NOT a unittest.assert* failure).
def breakOn(exc_name):
  exception = getattr(__builtin__, exc_name)
  def __new__(cls, *args, **kwds):
    # breakpoint(depth=1)
    pdbtrace()
    return exception(*args, **kwds)
  replacement = type(exc_name, (exception,), {'__new__': __new__})
  setattr(__builtin__, exc_name, replacement)

  if exc_name:
    breakOn(exc_name)

# ================================================================================
# It is now OK to load the curry module.

from .testcase import TestCase, FunctionalTestCase

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
      reload(curry)
  return decorator

