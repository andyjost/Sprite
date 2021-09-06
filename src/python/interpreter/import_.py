from .. import config
from .. import icurry
from .. import importer
from .. import objects
from ..common import T_FUNC, T_CTOR
from ..utility.currypath import clean_currypath
from ..utility import encoding, visitation, formatDocstring
import collections
import logging
import weakref

logger = logging.getLogger(__name__)

def insertSymbol(module, basename, nodeinfo, private=False):
  '''
  Inserts a symbol into the given module.

  All symbols are added to the module's '.symbols' dict.  Public symbols are
  also bound directly to the module itself.

  Parameters:
  -----------
  ``module``
      An instance of ``CurryModule``.
  ``basename``
      A stirng containing the unqualified symbol name.
  ``nodeinfo``
      The nodeinfo for this symbol.
  ``private``
      Whether this is a private symbol.

  Returns:
  --------
  Nothing.
  '''
  getattr(module, '.symbols')[basename] = nodeinfo
  if not private and encoding.isaCurryIdentifier(basename):
    setattr(module, basename, nodeinfo)

def loadSubmodules(interp, ipkg, package, extern, export, alias):
  for name in ipkg.submodules.keys():
    if not hasattr(package, name):
      moduleobj = import_(
          interp, ipkg[name], extern=extern, export=export, alias=alias
        )
      assert hasattr(package, name)

def updatePackage(interp, moduleobj):
  imodule = getattr(moduleobj, '.icurry')
  if imodule.package is not None:
    ipkg_from = imodule.package
    pkgobj = interp.modules[ipkg_from.fullname]
    assert not hasattr(pkgobj, imodule.name)
    setattr(pkgobj, imodule.name, moduleobj)
    ipkg_to = getattr(pkgobj, '.icurry')
    assert ipkg_to.fullname == ipkg_from.fullname
    ipkg_to.merge(ipkg_from, [imodule.name])
    imodule.setparent(ipkg_to)

@visitation.dispatch.on('idef')
def loadSymbols(interp, idef, moduleobj, extern=None, **kwds): #pragma: no cover
  '''
  Load symbols (i.e., constructor and functions names) from the ICurry
  definition ``idef`` into module ``moduleobj``.
  '''
  raise RuntimeError("unhandled ICurry type during symbol loading: '%s'" % type(idef))

@loadSymbols.when(collections.Sequence, no=(str))
def loadSymbols(interp, seq, *args, **kwds):
  return [loadSymbols(interp, item, *args, **kwds) for item in seq]

@loadSymbols.when(icurry.IDataType)
def loadSymbols(interp, itype, moduleobj, extern=None):
  # FIXME: why does the frontend translate empty types to a type with one
  # constructor?  The check for _Constr# below might need to be adjusted.  It
  # should indicate the presence of a type that requires an external
  # definition.
  if not itype.constructors or \
      (len(itype.constructors) == 1 and \
       itype.constructors[0].name.startswith('_Constr#')):
    if extern is not None and itype.name in extern.types:
      itype.constructors = extern.types[itype.name].constructors
    else:
      raise ValueError(
          '%r has no constructors and no external definition was found.'
              % itype.fullname
        )
  assert itype.constructors
  constructors = []
  constructors.extend(
      loadSymbols(
          interp, itype.constructors, moduleobj, extern, itype=itype
        , constructors=constructors
        )
    )
  typedef = objects.CurryDataType(itype.name, constructors, moduleobj)
  getattr(moduleobj, '.types')[itype.name] = typedef
  for i,ctor in enumerate(constructors):
    ctor.info.typedef = weakref.ref(typedef)
  return typedef

@loadSymbols.when(collections.Mapping)
def loadSymbols(interp, mapping, moduleobj, **kwds):
  return {
      k: loadSymbols(interp, v, moduleobj, **kwds)
        for k,v in mapping.iteritems()
    }

@loadSymbols.when(icurry.IModule)
def loadSymbols(interp, imodule, moduleobj, **kwds):
  for modulename in imodule.imports:
    import_(interp, modulename)
  icurry.analysis.set_monadic_metadata(imodule, interp.modules)
  loadSymbols(interp, imodule.types, moduleobj, **kwds)
  loadSymbols(interp, imodule.functions, moduleobj, **kwds)
  return moduleobj

@loadSymbols.when(icurry.IConstructor)
def loadSymbols(
    interp, icons, moduleobj, extern=None, itype=None, constructors=None
  ):
  # For builtins, the 'all.tag' metadata contains the tag.
  builtin = 'all.tag' in icons.metadata
  metadata = icurry.metadata.getmd(icons, extern, itype=itype)
  info = interp.context.runtime.InfoTable(
      icons.name
    , icons.arity
    , T_CTOR + icons.index if not builtin else metadata['all.tag']
    , _no_step if not builtin else _unreachable
    , getattr(metadata, 'py.format', None)
    , _gettypechecker(interp, metadata)
    , getattr(metadata, 'all.flags', 0)
    )
  nodeinfo = objects.CurryNodeLabel(icons, info)
  insertSymbol(moduleobj, icons.name, nodeinfo)
  return nodeinfo

@loadSymbols.when(icurry.IFunction)
def loadSymbols(interp, ifun, moduleobj, extern=None):
  metadata = icurry.metadata.getmd(ifun, extern)
  InfoTable = interp.context.runtime.InfoTable
  info = InfoTable(
      ifun.name
    , ifun.arity
    , T_FUNC
    , None
    , getattr(metadata, 'py.format', None)
    , _gettypechecker(interp, metadata)
    , InfoTable.MONADIC if metadata.get('all.monadic') else 0
    )
  nodeinfo = objects.CurryNodeLabel(ifun, info)
  insertSymbol(moduleobj, ifun.name, nodeinfo, ifun.is_private)
  return nodeinfo

@visitation.dispatch.on('arg')
@formatDocstring(__package__[:__package__.find('.')])
def import_(interp, arg, currypath=None, extern=True, export=(), alias=(), is_sourcefile=False):
  '''
  Import one or more Curry modules.

  Parameters:
  -----------
  ``arg``
      A module descriptor indicating what to import.  A module descriptor is a
      module name (string), ``{0}.icurry.IModule`` object, or a sequence of
      module descriptors.
  ``currypath``
      The search path for Curry files.  By default, ``self.path`` is used.
  ``extern``
      An instance of ``{0}.icurry.IModule`` used to resolve external
      declarations.
  ``export``
      A set of symbols exported unconditionally from ``extern``.  These will
      be copied into the imported module.
  ``alias``
      A set of name-target pairs specifying aliases.  For each alias, the
      module produced will have a binding called ``name`` referring to
      ``target``.
  ``is_sourcefile``
      Indicates whether to interpret ``arg`` as a sourcefile name rather than a
      module name.

  Returns:
  --------
  A ``CurryModule`` or sequence thereof.
  '''
  raise TypeError('cannot import type %r' % type(arg).__name__)

@import_.when(str)
def import_(interp, name, currypath=None, is_sourcefile=False, **kwds):
  try:
    return interp.modules[name]
  except KeyError:
    logger.info('Importing %s', name)
    if name == 'Prelude':
      prelude = interp.context.runtime.prelude
      kwds.setdefault('extern', prelude.Prelude)
      kwds.setdefault('export', prelude.exports())
      kwds.setdefault('alias', prelude.aliases())
    elif name == 'Control.SetFunctions':
      setfunctions = interp.context.runtime.setfunctions
      kwds.setdefault('extern', setfunctions.SetFunctions)
      kwds.setdefault('export', setfunctions.exports())
      kwds.setdefault('alias', setfunctions.aliases())
    currypath = clean_currypath(interp.path if currypath is None else currypath)
    icur = importer.loadModule(name, currypath, is_sourcefile=is_sourcefile)
    cymodule = import_(interp, icur, **kwds)
    return objects._Handle(cymodule).findmodule(name)

@import_.when(collections.Sequence, no=str)
def import_(interp, seq, *args, **kwds):
  return [import_(interp, item, *args, **kwds) for item in seq]

@import_.when(icurry.IPackage)
def import_(
    interp, ipkg, currypath=None, extern=None, export=(), alias=()
  ):
  if ipkg.fullname not in interp.modules:
    moduleobj = objects.CurryPackage(ipkg)
    interp.modules[ipkg.fullname] = moduleobj
  package = interp.modules[ipkg.fullname]
  updatePackage(interp, package)
  loadSubmodules(interp, ipkg, package, extern, export, alias)
  return package

@import_.when(icurry.IModule)
def import_(
    interp, imodule, currypath=None, extern=None, export=(), alias=()
  ):
  if imodule.fullname not in interp.modules:
    imodule.merge(extern, export)
    moduleobj = objects.CurryModule(imodule)
    interp.modules[imodule.fullname] = moduleobj
    updatePackage(interp, moduleobj)
    loadSymbols(interp, imodule, moduleobj, extern=extern)
    compileICurry(interp, imodule, moduleobj, extern=extern)
    for name, target in alias:
      if hasattr(moduleobj, name):
        raise ValueError("cannot alias previously defined name '%s'" % name)
      setattr(moduleobj, name, getattr(moduleobj, target))
  return interp.modules[imodule.fullname]

@visitation.dispatch.on('idef')
def compileICurry(interp, idef, moduleobj, extern=None): # pragma: no cover
  '''Compile the ICurry definitions from ``idef`` into module ``moduleobj``'''
  assert False

@compileICurry.when(collections.Mapping)
def compileICurry(interp, mapping, *args, **kwds):
  for item in mapping.itervalues():
   compileICurry(interp, item, *args, **kwds)

@compileICurry.when(icurry.IModule)
def compileICurry(interp, imodule, moduleobj, extern=None):
  compileICurry(interp, imodule.functions, moduleobj, extern)

@compileICurry.when(icurry.IFunction)
def compileICurry(interp, ifun, moduleobj, extern=None):
  info = objects._Handle(moduleobj).getsymbol(ifun.name).info
  # Compile interactive code right away.  Otherwise, if lazycompile is set,
  # delay compilation until the function is actually used.  See InfoTable in
  # interpreter/runtime.py.
  if interp.flags['lazycompile'] and \
      ifun.modulename != config.interactive_modname():
    # Delayed.
    info.step = LazyFunction(
        interp.context.compiler.compile_function, interp, ifun, extern
      )
  else:
    # Immediate.
    info.step = interp.context.compiler.compile_function(interp, ifun, extern)

def _no_step(*args, **kwds):
  pass

def _unreachable(*args, **kwds):
  assert False

# FIXME: several things in the info table now have an interpreter bound.  It
# would be great to simplify that.  Maybe it should just be added as an entry
# to the info table.
def _gettypechecker(interp, metadata):
  '''
  If debugging is enabled, and a typechecker is defined, get it and bind the
  interpreter.
  '''
  if interp.flags['debug']:
    checker = getattr(metadata, 'py.typecheck', None)
    if checker is not None:
      return lambda *args: checker(interp, *args)

class LazyFunction(tuple):
  def __new__(cls, *args):
    self = tuple.__new__(cls, args)
    return self
  def __repr__(self):
    return '<not yet compiled>'

