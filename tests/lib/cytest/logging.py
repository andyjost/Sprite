'''Facilities for checking log output.'''

from __future__ import absolute_import
from curry.utility.binding import binding
import collections
import contextlib
import curry
import importlib
import logging

class Logger(logging.Logger):
  '''
  A replacement for logging.Logger that captures output.  Keywords arguments to
  logger functions are not handled.
  '''
  def __init__(self):
    self._data = collections.defaultdict(list)

  def isEnabledFor(*args, **kwds):
    return True

  @staticmethod
  def _format(msg, args):
    return msg % args if args else msg

  def log(self, level, msg, *args):
    self._data[level].append(self._format(msg, args))

  def debug(self, msg, *args):
    self._data[logging.DEBUG].append(self._format(msg, args))

  def info(self, msg, *args):
    self._data[logging.INFO].append(self._format(msg, args))

  def warn(self, msg, *args):
    self._data[logging.WARNING].append(self._format(msg, args))

  def error(self, msg, *args):
    self._data[logging.ERROR].append(self._format(msg, args))

  def critical(self, msg, *args):
    self._data[logging.CRITICAL].append(self._format(msg, args))


class LogCapture(object):
  '''Context manager that captures log output.'''
  def __init__(self, *modulenames):
    self.logger = Logger()
    self.modulenames = modulenames
    self.__state = self.__initstate()

  @property
  def data(self):
    return self.logger._data

  def __initstate(self):
    bindings = []
    for modulename in self.modulenames:
      module = importlib.import_module(modulename)
      for loggername, obj in module.__dict__.iteritems():
        if isinstance(obj, logging.Logger):
          break
      else:
        raise TypeError(
            'no instance of logging.Logger found in module %s' % modulename
          )
      # This binding ensures that any new loggers created for the named module
      # will be the the instance prepared here.  This is needed when reloading
      # a module that uses logging.getLogger to generate a message.
      bindings += [binding(logging.Logger.manager.loggerDict, modulename, self.logger)]
      # This binding overrides the logger in the named module.
      bindings += [binding(getattr(module, '__dict__'), loggername, self.logger)]
    with contextlib.nested(*bindings):
      yield

  def __enter__(self):
    next(self.__state)
    return self

  def __exit__(self, *exc):
    try:
      next(self.__state)
    except StopIteration:
      pass
    return False

  def checkMessages(
      self
    , testcase, debug=None, info=None, warning=None, error=None, critical=None
    ):
    levels = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
    for lvl, required in zip(levels, [debug, info, warning, error, critical]):
      if required is not None:
        logged_msgs = self.data.get(lvl, [])
        for req in ([required] if isinstance(required, str) else required):
          if not any(req in msg for msg in logged_msgs):
            errmsg = [
                'not found in %s log output: %r'
                    % (logging.getLevelName(lvl), req)
              ]
            errmsg += ['Log output is:']
            for l in levels:
              if self.data.get(l) is not None:
                errmsg += ['    ' + logging.getLevelName(l) + ':']
                errmsg += ['        (%s) ' % i + s for i,s in enumerate(self.data.get(l))]
            testcase.assertTrue(False, msg='\n'.join(errmsg))

def capture_log(*args, **kwds):
  return LogCapture(*args, **kwds)

