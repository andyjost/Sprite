'''Code for importing Curry modules into a Curry interpreter.'''

from . import link, load
from ... import icurry, objects, toolchain
from ...objects.handle import getHandle
from ...utility.currypath import clean_currypath
from ...utility import visitation, formatDocstring, validateModulename
import collections, logging

logger = logging.getLogger(__name__)

__all__ = ['import_']

@visitation.dispatch.on('arg')
@formatDocstring(__package__[:__package__.find('.')])
def import_(
    interp, arg, currypath=None, extern=True, export=(), alias=()
  , is_sourcefile=False
  ):
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
  if is_sourcefile:
    if not name.endswith('.curry'):
      raise ValueError('expected a file name ending with .curry')
    modulename = name[:-len('.curry')]
  else:
    modulename = name
  validateModulename(modulename)
  try:
    return interp.modules[modulename]
  except KeyError:
    logger.info('Importing %s', modulename)
    if modulename == 'Prelude':
      prelude = interp.context.runtime.prelude
      kwds.setdefault('extern', prelude.Prelude)
      kwds.setdefault('export', prelude.exports())
      kwds.setdefault('alias', prelude.aliases())
    elif modulename == 'Control.SetFunctions':
      setfunctions = interp.context.runtime.setfunctions
      kwds.setdefault('extern', setfunctions.SetFunctions)
      kwds.setdefault('export', setfunctions.exports())
      kwds.setdefault('alias', setfunctions.aliases())
    currypath = clean_currypath(interp.path if currypath is None else currypath)
    icur = toolchain.loadicurry(name, currypath, is_sourcefile=is_sourcefile)
    cymodule = interp.import_(icur, **kwds)
    return getHandle(cymodule).findmodule(modulename)

@import_.when(collections.Sequence, no=str)
def import_(interp, seq, *args, **kwds):
  return [interp.import_(item, *args, **kwds) for item in seq]

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
    load.loadSymbols(interp, imodule, moduleobj, extern=extern)
    link.link(interp, imodule, moduleobj, extern=extern)
    for name, target in alias:
      if hasattr(moduleobj, name):
        raise ValueError("cannot alias previously defined name '%s'" % name)
      setattr(moduleobj, name, getattr(moduleobj, target))
  return interp.modules[imodule.fullname]

def loadSubmodules(interp, ipkg, package, extern, export, alias):
  for name in ipkg.submodules.keys():
    if not hasattr(package, name):
      moduleobj = interp.import_(
          ipkg[name], extern=extern, export=export, alias=alias
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

