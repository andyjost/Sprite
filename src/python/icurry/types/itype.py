from . import imodule
from .iobject import IArity
from .isymbol import ISymbol
from . import inspect
from ...utility import translateKwds
import weakref

__all__ = ['IConstructor', 'IDataType', 'IType']

class IDataType(ISymbol):
  @translateKwds({'name': 'fullname'})
  def __init__(self, fullname, constructors, **kwds):
    self.fullname = fullname
    self.constructors = [ctor.setparent(self, i) for i,ctor in enumerate(constructors)]
    ISymbol.__init__(self, **kwds)

  _fields_ = 'fullname', 'constructors'

  def setparent(self, parent):
    assert inspect.isa_module(parent)
    self.parent = weakref.ref(parent)
    return self

  def __str__(self):
    return 'data %s = %s' % (self.name, ' | '.join(map(str, self.constructors)))

IType = IDataType


class IConstructor(ISymbol):
  @translateKwds({'name': 'fullname'})
  def __init__(self, fullname, arity, **kwds):
    assert arity >= 0
    self.fullname = fullname
    self.arity = IArity(arity)
    ISymbol.__init__(self, **kwds)

  _fields_ = 'fullname', 'arity'

  def setparent(self, parent, index):
    assert isinstance(parent, IDataType)
    self.parent = weakref.ref(parent)
    self.index = index
    return self

  @property
  def typename(self):
    self.parent().fullname

  def __str__(self):
    return self.name + ' _' * self.arity
