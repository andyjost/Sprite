from . import imodule
from .iobject import IArity
from .isymbol import ISymbol
from ...utility import translateKwds
import weakref

__all__ = ['IConstructor', 'IDataType', 'IType']

class IDataType(ISymbol):
  @translateKwds({'name': 'fullname'})
  def __init__(self, fullname, constructors, **kwds):
    ISymbol.__init__(self, fullname, **kwds)
    self.constructors = [
        ctor._postinit_(i, fullname) for i,ctor in enumerate(constructors)
      ]

  _fields_ = 'fullname', 'constructors'

  @property
  def typename(self):
    return typename

  @property
  def children(self):
    return self.constructors

  def __str__(self):
    return 'data %s = %s' % (
        self.name, ' | '.join(str(x) for x in self.constructors)
      )

IType = IDataType


class IConstructor(ISymbol):
  @translateKwds({'name': 'fullname'})
  def __init__(self, fullname, arity, **kwds):
    ISymbol.__init__(self, fullname, **kwds)
    self.arity = IArity(arity)
    self.typename = kwds.pop('typename', None)

  _fields_ = 'fullname', 'arity', 'typename'

  def _postinit_(self, index, typename):
    self.index = index
    self.typename = typename
    return self

  def __str__(self):
    return self.name + ' _' * self.arity
