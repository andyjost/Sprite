from .iobject import IArity, IObject
from .isymbol import ISymbol
from ...utility.formatting import indent
from ...utility import translateKwds
import abc, six, weakref

__all__ = [
    'IBody', 'IExternal', 'IFuncBody', 'IFunction', 'IVisibility'
  , 'Private', 'PRIVATE', 'Public', 'PUBLIC'
  ]

class IFunction(ISymbol):
  @translateKwds({'name': 'fullname'})
  def __init__(self, fullname, arity, vis=None, needed=None, body=None, **kwds):
    ISymbol.__init__(self, fullname, **kwds)
    self.arity = IArity(arity)
    self.vis = PUBLIC if vis is None else vis
    # None means no info; [] means nothing needed.
    self.needed = None if needed is None else list(map(int, needed))
    self.body = body if body is not None else IExternal(fullname)

  _fields_ = 'fullname', 'arity', 'vis', 'needed', 'body'

  @property
  def is_private(self):
    return self.vis == PRIVATE

  @property
  def is_external(self):
    return isinstance(self.body, IExternal)

  def __str__(self):
    return '%s:\n%s' % (self.name, indent(self.body))


class Public(IObject):
  def __repr__(self):
    return "PUBLIC"
  def __str__(self):
    return "Public"
PUBLIC = Public()


class Private(IObject):
  def __repr__(self):
    return "PRIVATE"
  def __str__(self):
    return "Private"
PRIVATE = Private()


class IVisibility(six.with_metaclass(abc.ABCMeta, IObject)):
  pass
IVisibility.register(Public)
IVisibility.register(Private)


class IExternal(IObject):
  '''A link to external Curry function.'''
  @translateKwds({'name': 'symbolname'})
  def __init__(self, symbolname, **kwds):
    self.symbolname = str(symbolname)
    IObject.__init__(self, **kwds)
  def __str__(self):
    return 'extern(%s)' % self.symbolname
  def __repr__(self):
    return '%s(symbolname=%r)' % (type(self).__name__, self.symbolname)


class IFuncBody(six.with_metaclass(abc.ABCMeta, IObject)):
  def __init__(self, block, **kwds):
    self.block = block
    IObject.__init__(self, **kwds)
  @property
  def children(self):
    return self.block,
  def __str__(self):
    return str(self.block)
  def __repr__(self):
    return 'IFuncBody(block=%r)' % self.block
IFuncBody.register(IExternal)
IBody = IFuncBody
