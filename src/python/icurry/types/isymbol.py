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
    self._modulename = kwds.pop('modulename', None)
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
    return self.fullname.rpartition('.')[0]

  def splitname(self):
    '''
    Returns the components of the symbol path as a list.  For example,
    'Control.SetFunctions.evalS' returns ['Control', 'SetFunctions', 'evalS'].
    '''
    def gen():
      pkgname, _, modname = self.fullname.rpartition('.')
      for part in pkgname.split('.'):
        if part:
          yield part
      yield modname
    return list(gen())
    

class IContainer(ISymbol):
  '''Specialization of ISymbol for packages and modules.'''
  @property
  def modulename(self):
    return self.name

  @property
  def name(self):
    return self.fullname.rpartition('.')[2]

