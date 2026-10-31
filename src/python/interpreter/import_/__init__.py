'''Code for importing Curry modules into a Curry interpreter.'''

from ... import config, icurry, objects, toolchain, utility
from . import load
from ...objects.handle import getHandle
from ...toolchain import plans, _filenames, _findcurry
from ...utility.binding import binding
from ...utility import curryname, formatDocstring, visitation
import collections.abc, contextlib, logging, os, warnings
from ...exceptions import CurryWarning, StaleError
from ...utility.locking import native_metadata

logger = logging.getLogger(__name__)

def _warn(message, *args):
  logger.warning(message, *args)
  warnings.warn(message % args, CurryWarning, stacklevel=2)

__all__ = [
    'edited_source', 'import_', 'record_source', 'warn_edited'
  , 'warn_other_file'
  ]

@visitation.dispatch.on('arg')
@formatDocstring(config.python_package_name())
def import_(interp, arg, currypath=None, is_sourcefile=False):
  '''
  Import one or more Curry modules.

  Args:
    arg:
        A module descriptor indicating what to import.  A module descriptor is
        a module name (string), ``{0}.icurry.IModule`` object, or a sequence of
        module descriptors.
    currypath:
        The search path for Curry files.  By default, ``self.path`` is used.
    is_sourcefile:
        Indicates whether to interpret ``arg`` as a source file name rather
        than a module name.

  Returns:
    A :class:`CurryModule <{0}.objects.CurryModule>` or sequence thereof.
  '''
  raise TypeError('cannot import type %r' % type(arg).__name__)

# Import a module or package by name.
@import_.when(str)
def import_(interp, name, currypath=None, is_sourcefile=False):
  modulename = curryname.getModuleName(name, is_sourcefile)
  if is_sourcefile:
    _findcurry.reject_library_shadow(modulename, name, interp)
  elif modulename in config.syslibs():
    path = curryname.makeCurryPath(interp.path if currypath is None else currypath)
    plan = plans.makeplan(interp, plans.MAKE_ALL | plans.ZIP_JSON)
    filename = next(_findcurry._modulefiles(plan, modulename, path), None)
    if filename is not None and not os.path.isdir(filename):
      _findcurry.reject_library_shadow(
          modulename, _filenames.curryfilename(filename), interp)
  moduleobj = interp.modules.get(modulename)
  if moduleobj is None or isinstance(moduleobj, objects.CurryPackage):
    importEx = ImportEx(interp, currypath)
    if moduleobj is not None and not is_sourcefile:
      filename = next(_findcurry._modulefiles(
          importEx.plan, modulename, importEx.currypath), None)
      if filename is None or os.path.isdir(filename):
        return moduleobj
    if is_sourcefile:
      return importEx(name, is_sourcefile=is_sourcefile)
    else:
      prefixes = list(curryname.prefixes(modulename))
      return importEx(prefixes)
  else:
    # A loaded module is returned as it was loaded.  The file is not read
    # again; a warning says so when it changed (issue #110), or when the
    # file named is another file of the same module name.
    warn_edited(moduleobj)
    if is_sourcefile:
      warn_other_file(moduleobj, name)
    return moduleobj

# Import a sequence or specifiers.
@import_.when(collections.abc.Sequence, no=str)
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

  ``currypath`` is the search path of the import; by default the path of
  the interpreter.  A module given as a source file has its directory
  searched first, as PAKCS searches (``_findcurry.program_path``), and its
  imports are searched on that path, then on the path of the interpreter
  (``import_path``), so the imports of a program are found beside it, and
  a module of the library as before.  A module given by name is found on
  ``currypath`` alone, and its imports on the path of the interpreter, as
  before.  A parsed module (an ``IModule``) given with a path, as the steps
  of a plan give the module of a program, has its imports searched as a
  source file has.
  '''
  def __init__(self, interp, currypath):
    self.plan = plans.makeplan(interp, plans.MAKE_ALL | plans.ZIP_JSON)
    self.currypath = curryname.makeCurryPath(
        interp.path if currypath is None else currypath
      )
    # Whether the module was given by name (not as a file, not parsed).
    self.by_name = False

  @property
  def interp(self):
    return self.plan.interp

  @property
  def import_path(self):
    '''
    The search path of the imports of a module imported here.  For a module
    given as a source file, or parsed and given with a path: the path of
    this import (the directory of a file first), then the entries of the
    path of the interpreter that it lacks (``_findcurry.import_path``).
    None, the path of the interpreter, for a module given by name: the path
    given with a name finds that module alone.
    '''
    if self.by_name:
      return None
    return _findcurry.import_path(self.interp, self.currypath)

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

  @__call__.when(str)
  def __call__(self, modulename, tail=[], is_sourcefile=False):
    logger.info('Importing %s', modulename)
    if tail and not is_sourcefile:
      # A prefix denotes a namespace here, even when a module of that
      # name exists too. Loading that module can import this very child.
      for directory in utility.filesys.findfiles(
          self.currypath, modulename.replace('.', os.sep)):
        if os.path.isdir(directory):
          package = icurry.IPackage(modulename)
          package.filename = directory
          return self(package, tail)
    if is_sourcefile:
      self.currypath = _findcurry.program_path(
          modulename, self.currypath, is_sourcefile=True
        )
    else:
      self.by_name = True
    icontainer = toolchain.loadcurry(
        self.plan, modulename, self.currypath, is_sourcefile=is_sourcefile
      )
    moduleobj = self(icontainer, tail)
    return moduleobj

  @__call__.when(objects.CurryModule)
  def __call__(self, moduleobj, tail=[]):
    return self(tail, rv=moduleobj)

  @__call__.when(icurry.IPackage)
  def __call__(self, ipkg, tail=[]):
    pkgobj = native_metadata(self._finish_package)(ipkg)
    return self(tail, rv=pkgobj)

  def _finish_package(self, ipkg):
    existing = self.interp.modules.get(ipkg.fullname)
    if existing is not None:
      return existing
    with _provisionalModule(self.interp, ipkg) as pkgobj:
      return pkgobj

  @__call__.when(icurry.IModule)
  def __call__(self, imodule, tail=[]):
    session = self.interp._session
    if imodule.filename:
      _findcurry.reject_library_shadow(
          imodule.fullname, imodule.filename, self.interp)
    parents = list(curryname.prefixes(imodule.fullname))[:-1]
    for index, name in enumerate(parents):
      directory = os.path.dirname(imodule.filename or '')
      for _ in range(len(parents) - index - 1):
        directory = os.path.dirname(directory)
      package = icurry.IPackage(name)
      package.filename = directory
      native_metadata(self._finish_package)(package)
    # Imports can compile or wait for a heap: finish them before entering
    # the native metadata transaction. No partial module is published.
    existing = self.interp.modules.get(imodule.fullname)
    if existing is None or isinstance(existing, objects.CurryPackage):
      for modulename in imodule.imports:
        self.interp.import_(modulename, currypath=self.import_path)
    moduleobj = native_metadata(self._finish_module)(imodule, session)
    return self(tail, rv=moduleobj)

  def _finish_module(self, imodule, session):
    if session is not self.interp._session:
      raise StaleError('the interpreter was reset during an import; import again')
    existing = self.interp.modules.get(imodule.fullname)
    if existing is not None and not isinstance(existing, objects.CurryPackage):
      return existing
    toolchain.mergebuiltins(imodule, self.interp.backend)
    toolchain.validatemodule(imodule)
    # The provisional registry is local to this context, including symbol
    # resolution by the materializer. Other threads only see complete modules.
    registry = self.interp.modules
    with self.interp._private_modules():
      with _provisionalModule(self.interp, imodule) as moduleobj:
        # A namespace may have been needed by the imports of this module.
        # Its children stay reachable when the module takes its name.
        if isinstance(existing, objects.CurryPackage):
          for name in getHandle(existing).icurry:
            setattr(moduleobj, name, getattr(existing, name))
        record_source(moduleobj)
        load.loadSymbols(self.interp, imodule, moduleobj)
        from ...objects.classes import build_classes
        build_classes(self.interp, moduleobj)
        from ...objects.terms import raw_symbols
        with raw_symbols():
          for name, target in imodule.aliases.items():
            if hasattr(moduleobj, name):
              raise ValueError("cannot alias previously defined name %r" % name)
            setattr(moduleobj, name, getattr(moduleobj, target))
        imports = self.import_path
        if imports is None:
          imports = curryname.makeCurryPath(self.interp.path)
        self.interp.backend.module_loaded(self.interp, moduleobj, imports)
    # Native phase and publication share heap ownership with reset. No
    # Python lock is held while acquiring it, and evaluation is never here.
    with self.interp._state_lock:
      parent, _, local = imodule.fullname.rpartition('.')
      if parent:
        setattr(registry[parent], local, moduleobj)
        if isinstance(registry[parent], objects.CurryPackage):
          getattr(registry[parent], '.icurry')[local] = imodule
      registry[imodule.fullname] = moduleobj
    return moduleobj


def record_source(moduleobj):
  '''
  Records the modification time of the source file of a module at its import
  (Handle.source_mtime), so that ``edited_source`` can tell a later edit.  A
  module without a source file, or whose file cannot be read, records
  nothing.
  '''
  h = getHandle(moduleobj)
  filename = getattr(moduleobj, '.source_file', None) or h.icurry.filename
  try:
    h.source_mtime = None if not filename else os.stat(filename).st_mtime_ns
    if filename and filename.endswith('.curry'):
      with open(filename, encoding='utf-8') as stream:
        h.icurry._source_text = stream.read()
  except OSError:
    h.source_mtime = None

def _source_change(moduleobj):
  '''
  The source file of a loaded module and its modification time now, when the
  time differs from the one recorded at the import; else None.  The products
  of the module are not consulted: the background compile of the C++ backend
  writes them again from the edited source (backends.cxx.tiered), so their
  times do not answer the question.
  '''
  h = getHandle(moduleobj)
  stamp = h.source_mtime
  if stamp is None:
    return None
  filename = getattr(moduleobj, '.source_file', None) or h.icurry.filename
  try:
    mtime = os.stat(filename).st_mtime_ns
  except OSError:
    return None
  if mtime == stamp:
    return None
  return filename, mtime

def edited_source(moduleobj):
  '''
  The source file of a loaded module when the file changed after the import,
  else None.  An import of such a module returns the module as it was
  loaded; a new process reads the edited file.
  '''
  change = _source_change(moduleobj)
  return None if change is None else change[0]

def warn_edited(moduleobj, always=False):
  '''
  Logs a warning when the source of a loaded module changed after the
  import: the module stays as it was loaded, and the process does not read
  the file again.  The warning is logged once per edit of a module object
  (Handle.warned_mtime), so that the imports of other modules, and the
  expression module of every evaluation, do not repeat it; with ``always``
  it is logged on every call (the :load of the REPL prints it once per
  :load).  Returns the source file, or None when the file did not change.
  '''
  change = _source_change(moduleobj)
  if change is None:
    return None
  filename, mtime = change
  h = getHandle(moduleobj)
  if always or h.warned_mtime != mtime:
    h.warned_mtime = mtime
    _warn(
        'module %r was not read again: its source %s changed after the '
        'import; the module stays as it was loaded in this process, and a '
        'new process reads the edited file'
      , h.fullname, filename
      )
  return filename

def warn_other_file(moduleobj, filename):
  '''
  Logs a warning when ``filename``, the source file a caller named, is not
  the file the loaded module was read from: the module name is loaded
  already, and the file named is not read.  Returns True when it warned.
  '''
  loaded = getHandle(moduleobj).icurry.filename
  if not loaded or not filename:
    return False
  if os.path.realpath(loaded) == os.path.realpath(filename):
    return False
  _warn(
      'module %r was not read from %s: the module name is loaded already '
      'from %s, and the module stays as it was loaded in this process; a '
      'new process reads the other file'
    , getHandle(moduleobj).fullname, filename, loaded
    )
  return True


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
        if isinstance(packageicur, icurry.IPackage):
          with binding(packageicur, modulename, imodule) as bind3:
            yield obj
            bind3.commit()
        else:
          yield obj
        bind2.commit()
    else:
      yield obj
    bind1.commit()

