'''Abstract interface to a runtime system.'''

from . import config
import abc
import importlib

__all__ = ['Runtime']

class Runtime(object):
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
