from .ibody import IBuiltin
from .iobject import IArity, IObject
from .isymbol import ISymbol
from ...utility.formatting import indent
from ...utility import translateKwds
import abc, six, weakref

__all__ = ['IFunction', 'IVisibility', 'Private', 'PRIVATE', 'Public', 'PUBLIC']

class IFunction(ISymbol):
  @translateKwds({'name': 'fullname'})
  def __init__(self, fullname, arity, vis=None, needed=None, body=None, **kwds):
    ISymbol.__init__(self, fullname, **kwds)
    self.arity = IArity(arity)
    self.vis = PUBLIC if vis is None else vis
    # None means no info; [] means nothing needed.
    self.needed = None if needed is None else list(map(int, needed))
    self.body = body if body is not None else IBuiltin(self.metadata)

  _fields_ = 'fullname', 'arity', 'vis', 'needed', 'body'

  @property
  def name(self):
    return self.fullname[len(self.modulename)+1:]

  @property
  def packagename(self):
    return self.modulename.rpartition('.')[0]

  @property
  def is_private(self):
    return self.vis == PRIVATE

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

