from .iobject import IObject

__all__ = ['IContainer', 'ISymbol']

class ISymbol(IObject):
  '''
  A named IObject that may appear in a symbol table or package.  Has
  ``fullname``, ``modulename``, ``name``, and ``packagename`` attributes.
  Derived types include packages, modules, types, constructors, liteals, and
  functions.
  '''
  def __init__(self, fullname, **kwds):
    self.fullname = fullname
    IObject.__init__(self, **kwds)

  @property
  def modulename(self):
    return self._modulename

  @modulename.setter
  def modulename(self, modulename):
    if isinstance(self, IContainer):
      raise TypeError(
         'modulename cannot be set on %s objects' % type(self).__name__
       )
    assert self.fullname.startswith(modulename + '.')
    self._modulename = modulename
    for child in self.children:
      child.modulename = modulename
    return self

  @property
  def name(self):
    return self.fullname[len(self.modulename)+1:]

  @property
  def packagename(self):
    return self.modulename.rpartition('.')[0]


class IContainer(ISymbol):
  '''Specialization of ISymbol for packages and modules.'''
  @property
  def modulename(self):
    return self.name

  @property
  def name(self):
    return self.fullname.rpartition('.')[2]

