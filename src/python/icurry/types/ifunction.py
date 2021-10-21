from abc import ABCMeta
from .iobject import IArity, IObject
from .isymbol import ISymbol
from . import inspect
from ...utility.formatting import indent
from ...utility import translateKwds
import weakref

__all__ = ['IFunction', 'IVisibility', 'Private', 'PRIVATE', 'Public', 'PUBLIC']

class IFunction(ISymbol):
  @translateKwds({'name': 'fullname'})
  def __init__(self, fullname, arity, vis=None, needed=None, body=[], **kwds):
    assert arity >= 0
    self.fullname = fullname
    self.arity = IArity(arity)
    self.vis = PUBLIC if vis is None else vis
    # None means no info; [] means nothing needed.
    self.needed = None if needed is None else map(int, needed)
    self.body = body
    ISymbol.__init__(self, **kwds)

  _fields_ = 'fullname', 'arity', 'vis', 'needed', 'body'

  def setparent(self, parent):
    assert inspect.isa_module(parent)
    self.parent = weakref.ref(parent)
    return self

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


class IVisibility(IObject):
  __metaclass__ = ABCMeta
IVisibility.register(Public)
IVisibility.register(Private)

