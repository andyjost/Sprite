import abc

class ModuleSpecification(abc.ABC):

  @abc.abstractmethod
  def aliases(self):
    pass

  @abc.abstractmethod
  def exports(self):
    pass

  @abc.abstractmethod
  def extern(self):
    pass
