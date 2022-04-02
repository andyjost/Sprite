from .iobject import IObject

__all__ = ['IContainer', 'ISymbol']

class ISymbol(IObject):
  '''
  A named IObject that may appear in a symbol table or package.  Has
  ``fullname``, ``modulename``, ``name``, and ``packagename`` attributes.
  Derived types include packages, modules, types, constructors, literals, and
  functions.
  '''
  def __init__(self, fullname, **kwds):
    self.fullname = fullname
    self._modulename = kwds.pop('modulename', None)
    IObject.__init__(self, **kwds)

  @property
  def modulename(self):
    # The full module name, as in 'Prelude' or 'Data.List'.
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

  def splitname(self):
    '''
    Returns the components of the symbol path as a list.  For example,
    'Control.SetFunctions.evalS' returns ['Control', 'SetFunctions', 'evalS'].
    '''
    def gen():
      for part in self.modulename.split('.'):
        if part:
          yield part
      if not isinstance(self, IContainer):
        yield self.name
    return list(gen())
    

class IContainer(ISymbol):
  '''Specialization of ISymbol for packages and modules.'''
  @property
  def modulename(self):
    return self.fullname

  @property
  def name(self):
    return self.fullname.rpartition('.')[2]


