'''Code for importing Curry modules into a Curry interpreter.'''

from . import load
from ... import config, icurry, objects, toolchain, utility
from ...objects.handle import getHandle
from ...utility.binding import binding
from ...utility import curryname, formatDocstring, visitation
import collections, contextlib, logging, six

logger = logging.getLogger(__name__)

__all__ = ['import_']

@visitation.dispatch.on('arg')
@formatDocstring(config.python_package_name())
def import_(
    interp, arg, currypath=None, extern=None, exports=None, aliases=None
  , is_sourcefile=False
  ):
  '''
  Import one or more Curry modules.

  Args:
    arg:
        A module descriptor indicating what to import.  A module descriptor is
        a module name (string), ``{0}.icurry.IModule`` object, or a sequence of
        module descriptors.
    currypath:
        The search path for Curry files.  By default, ``self.path`` is used.
    extern:
        An instance of ``{0}.icurry.IModule`` used to resolve external
        declarations.
    exports:
        A set of symbols exported unconditionally from ``extern``.  These will
        be copied into the imported module.
    aliases:
        A set of name-target pairs specifying aliases.  For each alias, the
        module produced will have a binding called ``name`` referring to
        ``target``.
    is_sourcefile:
        Indicates whether to interpret ``arg`` as a source file name rather
        than a module name.

  Returns:
    A :class:`CurryModule <{0}.objects.CurryModule>` or sequence thereof.
  '''
  raise TypeError('cannot import type %r' % type(arg).__name__)

# Import a module or package by name.
@import_.when(six.string_types)
def import_(
    interp, name, currypath=None, is_sourcefile=False
  , extern=None, exports=None, aliases=None
  ):
  modulename = curryname.getModuleName(name, is_sourcefile)
  try:
    return interp.modules[modulename]
  except KeyError:
    importEx = ImportEx(interp, currypath, extern, exports, aliases)
    if is_sourcefile:
      return importEx(name, is_sourcefile=is_sourcefile)
    else:
      prefixes = list(curryname.prefixes(modulename))
      return importEx(prefixes)

# Import a sequence or specifiers.
@import_.when(collections.Sequence, no=str)
def import_(interp, seq, *args, **kwds):
  return [interp.import_(item, *args, **kwds) for item in seq]

# Import an ICurry package.
@import_.when(icurry.IPackage)
def import_(interp, ipkg, currypath=None, **kwds):
  importEx = ImportEx(interp, currypath, **kwds)
  return importEx(ipkg)

# Import an ICurry module.
@import_.when(icurry.IModule)
def import_(interp, imodule, currypath=None, **kwds):
  importEx = ImportEx(interp, currypath, **kwds)
  return importEx(imodule)


class ImportEx(object):
  '''
  Low-level routine to import Curry packages and modules.
  '''
  def __init__(self, interp, currypath, extern=None, exports=None, aliases=None):
    self.interp = interp
    self.currypath = curryname.makeCurryPath(
        interp.path if currypath is None else currypath
      )
    self.extern = extern
    self.exports = set() if exports is None else exports
    self.aliases = {} if aliases is None else aliases

  @visitation.dispatch.on('arg')
  def __call__(self, arg, *args, **kwds):
    assert False

  @__call__.when(list)
  def __call__(self, seq, rv=None):
    if seq:
      obj = seq.pop(0)
      return self(obj, tail=seq)
    else:
      return rv

  @__call__.when(six.string_types)
  def __call__(self, modulename, tail=[], is_sourcefile=False):
    logger.info('Importing %s', modulename)
    icontainer = toolchain.loadicurry(
        modulename, self.currypath, is_sourcefile=is_sourcefile
      )
    if isinstance(icontainer, icurry.IModule):
      toolchain.mergebuiltins(icontainer, self.interp.backend)
      # toolchain.mergemodule(icontainer, self.extern, self.exports, self.aliases)
    moduleobj = self(icontainer, tail)
    return moduleobj

  @__call__.when(icurry.IPackage)
  def __call__(self, ipkg, tail=[]):
    if ipkg.fullname not in self.interp.modules:
      with _provisionalModule(self.interp, ipkg) as pkgobj:
        return self(tail, rv=pkgobj)
    else:
      pkgobj = self.interp.modules[ipkg.fullname]
      return self(tail, rv=pkgobj)

  @__call__.when(icurry.IModule)
  def __call__(self, imodule, tail=[]):
    if imodule.fullname not in self.interp.modules:
      toolchain.mergemodule(imodule, self.extern, self.exports, self.aliases)
      with _provisionalModule(self.interp, imodule) as moduleobj:
        load.loadSymbols(self.interp, imodule, moduleobj)
        for name, target in imodule.aliases:
          if hasattr(moduleobj, name):
            raise ValueError("cannot alias previously defined name %r" % name)
          setattr(moduleobj, name, getattr(moduleobj, target))
        return self(tail, rv=moduleobj)
    else:
      moduleobj = self.interp.modules[imodule.fullname]
      return self(tail, rv=moduleobj)


@contextlib.contextmanager
@utility.formatDocstring(config.python_package_name())
def _provisionalModule(interp, imodule):
  '''
  Context manager that creates a provisional :class:`CurryModule
  <{0}.objects.CurryModule>`.

  The provisional module is inserted into interp.modules and its parent
  package, if any.  If the context exits abnormally then those changes are
  rolled back.
  '''
  obj = objects.create_module_or_package(interp, imodule)
  with binding(interp.modules, imodule.fullname, obj) as bind1:
    packagename, _, modulename = imodule.fullname.rpartition('.')
    if packagename:
      packageobj = interp.modules[packagename]
      packageicur = getattr(packageobj, '.icurry')
      with binding(packageobj.__dict__, modulename, obj) as bind2:
        with binding(packageicur, modulename, imodule) as bind3:
          yield obj
          bind3.commit()
        bind2.commit()
    else:
      yield obj
    bind1.commit()

