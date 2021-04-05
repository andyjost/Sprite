from ..exceptions import TimeoutError
from .. import config
import contextlib
import logging
import os
import signal
import sys

logger = logging.getLogger(__name__)

__all__ = ['carp', 'handle_program_errors', 'make_exception']

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

def carp(exception, program_name=None, hint_timeout_sec=1, hint_kwds={}):
  '''Display an exception and exit with the given status value, unless it is None.'''
  def write_ln(*args, **kwds):
    if program_name is not None:
      sys.stderr.write('%s: ' % program_name)
    sys.stderr.write(*args, **kwds)

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

def handle_program_errors(*args, **kwds):
  return ProgramErrorHandler(*args, **kwds)

class ProgramErrorHandler(object):
  def __init__(self, program_name, exit_status=1, hint_timeout_sec=1, hint_kwds={}):
    self.program_name = program_name
    self.exit_status = exit_status
    self.hint_timeout_sec = hint_timeout_sec
    self.hint_kwds = hint_kwds
    self.nerrors = 0
  def print_error(self, exc_type, exc_value, exc_tb):
    carp(exc_value, self.program_name, self.hint_timeout_sec, self.hint_kwds)
  def __enter__(self):
    return self
  def __exit__(self, exc_type, exc_value, exc_tb):
    if exc_type:
      self.nerrors += 1
      self.print_error(exc_type, exc_value, exc_tb)
      if self.exit_status is None:
        return True
      elif not config.debugging():
        sys.exit(self.exit_status)
      # else reraise the exception

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
