from .isymbol import ISymbol
from . import inspect
from abc import ABCMeta
from collections import OrderedDict
from ...utility import translateKwds
import weakref

# Note: 'from curry.types import *' must import all dependencies needed to
# reconstruct a dump of ICurry.  For this purpose, OrderedDict is included.
__all__ = ['IModule', 'IModuleFacade', 'IProg', 'OrderedDict']

# FIXME: it looks like this can be merged into ISymbol.
class IPackageOrModule(ISymbol):
  def setparent(self, parent):
    if parent is None:
      del self.__dict__['parent']
    else:
      assert inspect.isa_package(parent)
      self.parent = weakref.ref(parent)
    return self

  @property
  def package(self):
    if hasattr(self, 'parent'):
      parent = self.parent()
      assert inspect.isa_package(parent)
      return parent

class IModule(IPackageOrModule):
  @translateKwds({'name': 'fullname'})
  def __init__(self, fullname, imports, types, functions, filename=None, **kwds):
    '''
    Parameters:
    -----------
      fullname    The fully-qualified module name.
      imports     A list of imported module names.
      types       A mapping or sequence of pairs: str -> [IConstructor].
      functions   A sequence of IFunctions, or a mapping or sequence of pairs
                  from string to IFunction.
    '''
    self.fullname = str(fullname)
    self.imports = tuple(set(str(x) for x in imports))
    self.types = symboltable(self, types)
    self.functions = symboltable(self, functions)
    self.filename = str(filename) if filename is not None else None
    ISymbol.__init__(self, **kwds)

  _fields_ = 'fullname', 'filename', 'imports', 'types', 'functions'

  def __str__(self):
    return '\n'.join(
        [
            'Module:'
          , '-------'
          , '  name: %s' % self.name
          , '  fullname: %s' % self.fullname
          , '  imports: %s' % ', '.join(self.imports)
          , ''
          , '  types:'
          , '  ------'
          ]
      + [   '    ' + str(ty) for ty in self.types.values() ]
      + [
            ''
          , '  functions:'
          , '  ----------'
          ]
      + [   '    ' + line for func in self.functions.values()
                          for line in str(func).split('\n')
          ]
      )

  def merge(self, extern, export):
    '''
    Copies the symbols specified in ``export`` from ``extern`` into this
    module.
    '''
    for name in export:
      found = 0
      for to,from_ in zip(*[[m.types, m.functions] for m in [self, extern]]):
        try:
          to[name] = from_[name]
        except KeyError:
          pass
        else:
          found += 1
      if not found:
        raise TypeError('cannot import %r from module %r' % (name, extern.fullname))

IProg = IModule

class IModuleFacade(IModule):
  '''
  A module in which every IFunction body is an instance of IMaterial.  Used for
  loading compiled code.
  '''
  def __init__(self, *args, **kwds):
    self.icurry = kwds.pop('icurry')
    IModule.__init__(self, *args, **kwds)
    for ifun in self.functions.values():
      if not isinstance(ifun.body, IMaterial):
        ifun.body = IMaterial(ifun.body)

def symboltable(parent, objs):
  if isinstance(objs, OrderedDict):
    return objs
  else:
    return OrderedDict(
        (v.name, v) for v in (v.setparent(parent) for v in objs)
      )

