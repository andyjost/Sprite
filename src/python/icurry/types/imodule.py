from ...exceptions import ModuleLookupError
from .isymbol import IContainer
from ...utility import translateKwds, visitation
import collections, itertools, six, weakref

OrderedDict = collections.OrderedDict

# Note: 'from curry.types import *' must import all dependencies needed to
# reconstruct a dump of ICurry.  For this purpose, OrderedDict is included.
__all__ = ['IModule', 'IPackage', 'IProg', 'OrderedDict']

class IModule(IContainer):
  @translateKwds({'name': 'fullname'})
  def __init__(
      self, fullname, imports, types, functions, filename=None, aliases=None, **kwds
    ):
    '''
    Args:
      fullname:   The fully-qualified module name.
      imports:    A list of imported module names.
      types:      A mapping or sequence of pairs: str -> [IConstructor].
      functions:  A sequence of IFunctions, or a mapping or sequence of pairs
                  from string to IFunction.
      aliases     A mapping from symbol names to symbol names.
    '''
    IContainer.__init__(self, fullname, **kwds)
    self.imports = tuple(set(str(x) for x in imports))
    self.types = _makeSymboltable(self, types)
    self.functions = _makeSymboltable(self, functions)
    self.filename = str(filename) if filename is not None else None
    self.aliases = {} if aliases is None else dict(aliases)

  _fields_ = 'fullname', 'filename', 'imports', 'types', 'functions', 'aliases'

  @staticmethod
  def fromBOM(
      fullname, imports, types, functions, mdkey, filename=None, aliases=None
    , **kwds
    ):
    '''
    Construct a module from its bill-of-materials.

    This prepares a special pre-compiled module that can be passed to the
    ``import_`` function.

    Each data type, constructor, and function is tagged with the metadata
    ``mdkey`` referring to the corresponding object in the bill of materials.
    The ``materialize`` function should intercept these and simply return the
    referred item.
    '''
    from . import IConstructor, IDataType, IFunction, IBody, IExempt
    itypes = [
        IDataType(
            '%s.%s' % (fullname, typeinfo.name)
          , [ IConstructor(
                  '%s.%s' % (fullname, ctorinfo.name), ctorinfo.arity
                , metadata=dict(ctor_md, **{mdkey: ctorinfo})
                )
                for ctor_md, ctorinfo in zip(ctor_mds, typeinfo.constructors)
              ]
          , metadata=dict(type_md, **{mdkey: typeinfo})
          )
          for type_md, ctor_mds, typeinfo in types
      ]
    ifunctions = [
        IFunction(
            '%s.%s' % (fullname, funcinfo.name), funcinfo.arity, vis, None
          , IBody(IExempt()), metadata=dict(md, **{mdkey: funcinfo})
          )
          for vis, md, funcinfo in functions
      ]
    imodule = IModule(
        fullname, imports, itypes, ifunctions, filename, aliases, **kwds
      )
    return imodule

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

IProg = IModule


class IPackage(IContainer, dict):
  '''
  A container for subpackages and/or modules.
  '''
  def __init__(self, fullname, **kwds):
    IContainer.__init__(self, fullname, **kwds)
    dict.__init__(self)

  _fields_ = 'fullname', 'submodules'

  @property
  def submodules(self):
    return self

  @property
  def children(self):
    return self.submodules.values()

  def __str__(self):
    return '\n'.join(
        [
            'Package:'
          , '--------'
          , '  name: %s' % self.name
          , '  fullname: %s' % self.fullname
          , '  keys: %s' % sorted(self.submodules.keys())
          , ''
          , '  submodules:'
          , '  -----------'
          ]
      + [   '    ' + line for key in sorted(self)
                          for line in str(self[key]).split('\n')
          ]
      )


@visitation.dispatch.on('objs')
def _makeSymboltable(parent, objs):
  assert False

@_makeSymboltable.when(collections.Iterable)
def _makeSymboltable(parent, objs):
  return _makeSymboltable(parent, list(objs))

@_makeSymboltable.when(collections.Mapping)
def _makeSymboltable(parent, objs):
  for v in six.itervalues(objs):
    v.modulename = parent.fullname
  return objs

@_makeSymboltable.when(collections.Sequence)
def _makeSymboltable(parent, objs):
  for v in objs:
    v.modulename = parent.fullname
  return OrderedDict((v.name, v) for v in objs)

