'''
Abstract interface to the runtime system.

This contains definitions common to all backends and the interfaces each should
implement.
'''

from . import config
import abc
import importlib

__all__ = [
    'Runtime'
  , 'T_FAIL', 'T_BIND', 'T_FREE', 'T_FWD', 'T_CHOICE', 'T_FUNC', 'T_CTOR'
  ]

T_FAIL   = -6
T_BIND   = -5
T_FREE   = -4
T_FWD    = -3
T_CHOICE = -2
T_FUNC   = -1
T_CTOR   =  0 # for each type, ctors are numbered starting at zero.


class Runtime(object):
  '''Abstract interface for a runtime system.'''
  __metaclass__ = abc.ABCMeta

  def __new__(cls, backend='py'):
    if cls is Runtime:
      currypkg = config.python_package_name()
      api = importlib.import_module('%s.backends.%s.runtime.api' % (currypkg, backend))
      return api.Runtime()
    else:
      return object.__new__(cls)

  @abc.abstractproperty
  def Node(self):
    assert 0

  @abc.abstractproperty
  def InfoTable(self):
    assert 0

  @abc.abstractproperty
  def prelude(self):
    assert 0

  @abc.abstractmethod
  def get_stepper(self):
    assert 0

  @abc.abstractmethod
  def get_step_counter(self):
    assert 0

class Node(object):
  __metaclass__ = abc.ABCMeta

class InfoTable(object):
  __metaclass__ = abc.ABCMeta
  
