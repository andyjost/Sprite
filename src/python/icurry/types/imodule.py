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
  def __init__(self, fullname, imports, types, functions, filename=None, **kwds):
    '''
    Args:
      fullname:    The fully-qualified module name.
      imports:     A list of imported module names.
      types:       A mapping or sequence of pairs: str -> [IConstructor].
      functions:   A sequence of IFunctions, or a mapping or sequence of pairs
                  from string to IFunction.
    '''
    # self.fullname = str(fullname)
    IContainer.__init__(self, fullname, **kwds)
    self.imports = tuple(set(str(x) for x in imports))
    self.types = _makeSymboltable(self, types)
    self.functions = _makeSymboltable(self, functions)
    self.filename = str(filename) if filename is not None else None

  _fields_ = 'fullname', 'filename', 'imports', 'types', 'functions'

  @staticmethod
  def fromBOM(fullname, imports, types, functions, mdkey, filename=None):
    '''
    Construct a module from the bill of materials.  The Curry functions should
    be implemented as native functions of the backend (e.g., Python function
    objects if the Python backend is used).  A module is constructed in which
    each function is implemented as IMaterial.  Finally, the true ICurry
    for this module is loaded and attached to attribute 'icurry'.
    '''
    from . import IConstructor, IDataType, IFunction, IBody, IExempt, PUBLIC
    from ... import toolchain
    itypes = [
        IDataType(
            '%s.%s' % (fullname, typeinfo.name)
          , [ IConstructor(
                  '%s.%s' % (fullname, ctorinfo.name), ctorinfo.arity
                , metadata={mdkey: ctorinfo}
                )
                for ctorinfo in typeinfo.constructors
              ]
          , metadata={mdkey: typeinfo}
          )
          for typeinfo in types
      ]
    ifunctions = [
        IFunction(
            '%s.%s' % (fullname, funcinfo.name), funcinfo.arity, PUBLIC, None
          , IBody(IExempt()), metadata={mdkey: funcinfo}
          )
          for funcinfo in functions
      ]
    # # makefun = lambda name, arity, vis, needed, func: \
    # #     IFunction(
    # #         name, arity, vis, needed
    # #       , IMaterial(func) if not isinstance(func, IMaterial) else func
    # #       )
    imodule = IModule(fullname, imports, itypes, ifunctions, filename)

    # for info in types:
    #   imodule.types[info.name].update_metadata({'py.material': info})
    # for info in functions:
    #   imodule.functions[info.name].update_metadata({'py.material': info})

    # try:
    #   imodule.icurry = toolchain.loadicurry(fullname)
    # except ModuleLookupError:
    #   imodule.icurry = None

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

  def copy_exported_names(self, extern, export):
    '''
    Copies exported functions and types, as specified in ``export``, from
    ``extern`` into this module.
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

  def merge(self, extern, merge_metadata=True, resolve_externals=True):
    '''
    Merges metadata and external symbols from ``extern``.
    '''
    from .. import metadata
    for itype in self.types.values():
      if merge_metadata:
        metadata.merge(itype, extern)
    for ifun in self.functions.values():
      if ifun.is_external and resolve_externals:
        if extern is None or ifun.name not in extern.functions:
          raise TypeError('failed to resolve external function %r' % ifun.fullname)
        ifun.body = extern.functions[ifun.name].body
      if merge_metadata:
        metadata.merge(ifun, extern)

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

