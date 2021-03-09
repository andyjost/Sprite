from ..exceptions import TimeoutError
from .. import config
import contextlib
import logging
import os
import signal
import sys

logger = logging.getLogger(__name__)

__all__ = ['die', 'handle_program_errors', 'make_exception']

def make_exception(ExcClass, message, hint=None):
  '''
  Create an exception object with a hint attached.

  Hints are only evaluated when an exception reaches the main function of a
  program.
  '''
  exc = ExcClass(message)
  if hint is not None:
    exc.hint = hint
  return exc

def die(exception, program_name=None, status=1, hint_timeout_sec=1, hint_kwds={}):
  '''Display an exception and exit with the given status value.'''
  def write_ln(*args, **kwds):
    if program_name is not None:
      sys.stderr.write('%s: ' % program_name)
    sys.stderr.write(*args, **kwds)

  if config.debugging():
    raise
  else:
    write_ln('%s\n' % exception)
    # If a hint attribute was attached to the exception, then evaluate it and
    # display the result.
    if hasattr(exception, 'hint'):
      try:
        hint = exception.hint
        if callable(hint):
          # A timeout is used to cap the time for calculating the hint.  this
          # is disabled for now.
          with timeout(0 and hint_timeout_sec):
            hint = hint(**hint_kwds)
        if hint:
          write_ln('Hint: %s\n' % hint)
      except BaseException as e:
        logger.debug(
            'An error occurred while evaluating exception hint %s: %s'
                % (hint, str(e))
          )
  sys.exit(status)

@contextlib.contextmanager
def handle_program_errors(*args, **kwds):
  try:
    yield
  except BaseException as e:
    die(e, *args, **kwds)

class timeout:
  def __init__(self, seconds):
    self.seconds = seconds
    self.message = 'timeout after %s sec' % seconds
  def handle_timeout(self, signum, frame):
    raise TimeoutError(self.message)
  def __enter__(self):
    self.prev = signal.signal(signal.SIGALRM, self.handle_timeout)
    signal.alarm(self.seconds)
  def __exit__(self, type, value, traceback):
    signal.alarm(0)
    signal.signal(signal.SIGALRM, self.prev)
