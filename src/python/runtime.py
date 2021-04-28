import abc

class Runtime(object):
  __metaclass__ = abc.ABCMeta
  # def __init__(self, backend='py'):

  @abc.abstractproperty
  def Node(self):
    assert 0

  @abc.abstractproperty
  def NodeInfo(self):
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
