from ..exceptions import ModuleLookupError, PrerequisiteError
from .. import config
from . import _filenames
from ..tools.utility import make_exception
from ..utility import curryname, filesys, formatDocstring
import logging, os

__all__ = ['currentfile', 'import_path', 'imports_path', 'program_path']
logger = logging.getLogger(__name__)
SUBDIR = config.intermediate_subdir()

def reserved_module_names():
  from ..backends.cxx import curryrtbindings as curryrt
  return curryrt.builtin_module_names()

def reject_library_shadow(modulename, filename, interp):
  if filename is not None and os.path.isfile(filename):
    modulename = _filenames.module_name(filename)
  if interp is None or modulename not in reserved_module_names() \
      or _installed_library_file(filename):
    return
  libraryfile = config.installed_path(
      'curry', modulename.replace('.', os.sep) + '.curry')
  raise ModuleLookupError(
      "Curry module %r from %r has the name of a module the runtime implements; "
      "the installed module %r cannot be replaced."
      % (modulename, os.path.abspath(filename), libraryfile)
    )

def _installed_library_file(filename):
  if filename is None:
    return False
  # Native module identity belongs to this installation. The source path
  # used to classify build products can be a different tree.
  root = os.path.realpath(config.installed_path('curry'))
  path = os.path.realpath(filename)
  return path == root or path.startswith(root + os.sep)

def _modulefiles(plan, name, currypath):
  '''Files in path order, then namespace directories from the whole path.'''
  curryname.validateModulename(name)
  parts = name.split('.')
  package_path, local = os.sep.join(parts[:-1]), parts[-1]
  names = [
      os.path.join(package_path, '.curry', SUBDIR, local + suffix)
          for suffix in reversed(plan.suffixes[1:])
    ]
  names += [os.path.join(package_path, local + '.curry')]
  currypath = list(currypath)
  for filename in filesys.findfiles(currypath, names):
    if os.path.isfile(filename):
      yield filename
  for directory in filesys.findfiles(
      currypath, [os.path.join(package_path, local, '')]):
    if os.path.isdir(directory):
      yield directory

def program_path(name, currypath, is_sourcefile=False, **ignored):
  '''
  The search path of a program.  For a module given as a source file
  (``is_sourcefile``), the root of the module hierarchy comes first, then the
  entries of ``currypath``, as PAKCS searches: the imports of the program
  are found beside it without a CURRYPATH that names its directory.  For a
  module given by name the path is ``currypath`` as a list.  The tools
  (sprite-exec, sprite-make) and curry.import_ of a path search this path
  for the imports of the program, and the plan asks the steps about the
  files of the program under it.
  '''
  currypath = list(currypath)
  if is_sourcefile:
    from . import _frontend
    directory = _frontend.source_root(name)
    currypath = [directory] + [
        entry for entry in currypath if os.path.abspath(entry) != directory
      ]
  return currypath

def imports_path(currypath, is_sourcefile=False, **ignored):
  '''
  The search path of the imports of a module whose own search path is
  ``currypath`` (``program_path``), as the steps of a plan import them.
  For a program given as a source file it is that path, so the imports are
  found beside the program.  None, the path of the interpreter, for a
  module given by name: the path given with a name finds that module
  alone, and its imports are searched as before.
  '''
  return list(currypath) if is_sourcefile else None

def import_path(interp, currypath):
  '''
  The search path of the imports of a program on ``currypath``
  (``imports_path``): that path, then the entries of the path of ``interp``
  it lacks.  So the imports of a program are found beside it and on the
  path given for it, and the Prelude and the other modules of the library
  as before, whatever path a caller gave.  None, the path of the
  interpreter, without a path.
  '''
  if currypath is None:
    return None
  path = curryname.makeCurryPath(currypath)
  for entry in curryname.makeCurryPath(interp.path):
    if entry not in path:
      path.append(entry)
  return path

@formatDocstring(config.python_package_name())
def currentfile(
    plan, name, currypath, is_sourcefile=False, **ignored
  ):
  '''
  Finds a current prerequisite along the Curry build pipeline.

  The file returned is the newest among the Curry source file (suffix: .curry),
  the ICurry file (suffix: .icy), the module image (suffix: .img),
  and the files of the backend (suffix: .cpp and .so), less the files
  that a step of the plan refuses (see ``Plan.prune_stale``) and the files
  made from them.  The C++ backend selects the last accepted stage in pipeline order.
  Generated C++ and objects carry receipts for source, route, budget and
  sorted registered primitive names.
  A newer sibling image does not hide a current object. Other backends
  retain modification-time selection.

  Args:
    plan:
        The compile plan.
    name:
        The module, source file, or package name.
    currypath:
        A sequence of paths to search (i.e., CURRYPATH split on ':').
    is_sourcefile:
        Indicates whether to interpret the name as a source file.  If True, the
        name should end with extension .curry.  Otherwise the name is
        interpreted as a module or package name.
    plan:
        The compilation :class:`plan <{0}.toolchain.plan.Plan>`  This indicates
        which files to consider as prerequisites.  If None, a default plan

  Raises:
    ModuleLookupError: the module was not found.

  Returns:
    The name of a module image file (suffix: .img), Curry source file (suffix:
    .curry), Python file (suffix: .py), C++ source (suffix: .cpp) or object
    (suffix: .so), or directory.  The image file is returned if it is
    up-to-date, otherwise, the
    Curry file is returned if it exists.  If neither of those applies, the
    package directory name is returned, if it exists.
  '''
  modulename = curryname.getModuleName(name, is_sourcefile)
  currypath = program_path(name, currypath, is_sourcefile)
  if not is_sourcefile:
    # If name is a module name, then search CURRYPATH for the source file or
    # (possibly zipped) image and set it as the name.  source file and
    # is_sourcefile=True.  It is acceptable to use an image file that has no
    # corresponding source file.  This means a library could be installed as
    # images and ICurry records, without needing to install its Curry source.
    files = _modulefiles(plan, name, currypath)
    try:
      name = next(files)
    except StopIteration:
      raise make_exception(
          ModuleLookupError
        , 'Curry module %r not found.' % name
        , hint=lambda:_fileNotFoundHint(name)
        )
    if os.path.isdir(name):
      return name
    else:
      name = _filenames.curryfilename(name)

  # Select a current prerequisite.
  curryfile = name
  if not curryfile.endswith('.curry'):
    raise ModuleLookupError('expected .curry extension in %r' % curryfile)
  curryfile = os.path.abspath(curryfile)
  reject_library_shadow(modulename, curryfile, plan.interp)
  filelist = plan.filelist(curryfile)
  from . import _curry2icurry, _interfaces
  icyfile = _filenames.icurryfilename(curryfile)
  source_changed = os.path.isfile(curryfile) and not \
      _curry2icurry.source_matches(curryfile, icyfile)
  if plan.stages[0].step is _curry2icurry.curry2icurry \
      and (source_changed or (
          os.path.isfile(curryfile) and not os.path.isfile(icyfile)
          and not _interfaces.is_current(icyfile, currypath))):
    # Check even when tidy removed the ICurry prerequisite.
    filelist = [curryfile]
  # Force recompile, if requested.
  if config.force_recompile_cxx():
    filelist = [
        fn for fn in filelist
           if not any(fn.endswith(suffix) for suffix in ['.cpp', config.module_object_suffix()])
      ]
  # Disregard a file the toolchain no longer accepts, and everything made
  # from it: a .cpp file of another format, or a .so file compiled against
  # other runtime headers.  The age of the runtime library does not count.
  from . import plans
  if plan.interp is not None and plan.flags & plans.MAKE_TARGET_SOURCE \
      and not source_changed and os.path.isfile(curryfile):
    # Refresh direct imports before judging their interfaces. Importing an
    # unchanged B must also see A's newly translated interface when A's
    # source changed but nobody has imported A yet.
    try:
      names = _interfaces.imports(icyfile) if os.path.isfile(icyfile) else \
          list(_interfaces.read(icyfile + _interfaces.SUFFIX) or {})
    except (OSError, ValueError):
      names = [] # the normal reader diagnoses a malformed ICurry file
    plan.interp.import_(names, currypath=import_path(plan.interp,
        imports_path(currypath, is_sourcefile)))
    if os.path.isfile(curryfile) and not os.path.isfile(icyfile) \
        and not _interfaces.is_current(icyfile, currypath):
      filelist = [curryfile]
  filelist = plan.prune_stale(
      filelist, imports_path(currypath, is_sourcefile)
    )
  if _curry2icurry.in_system_library(curryfile) and _curry2icurry.source_matches(
      curryfile, _filenames.icurryfilename(curryfile)):
    # pip extracts sources after .curry products and resets their times.
    # An unchanged shipped source with validated products follows the plan
    # order. prune_stale above still checks interfaces, formats and ABI.
    prereq = next((fn for fn in reversed(filelist) if os.path.isfile(fn)), curryfile)
  else:
    if plan.interp is not None and plan.interp.backend.backend_name == 'cxx':
      prereq = next((fn for fn in reversed(filelist) if os.path.isfile(fn)), curryfile)
    else:
      prereq = filesys.newest(filelist)
  prereq = os.path.abspath(prereq)
  if not os.path.exists(prereq):
    # If there is no prerequisite, then there is no Curry file or any of its
    # derivatives (it could be OK to ship Curry files with no source).  Report
    # this as there being no source file.
    assert not os.path.exists(curryfile)
    raise ModuleLookupError('Curry file does not exist: %r' % curryfile)
  if not (os.access(prereq, os.R_OK) and os.path.isfile(prereq)):
    raise PrerequisiteError(
        'prerequisite is the wrong type or is unreadable: %r' % prereq
      )
  logger.debug('Prerequisite for compilation of %r is %r', name, prereq)
  return prereq

# Keyword defaults.
def _fileNotFoundHint(name, **kwds):
  if os.path.exists(name + '.curry'):
    return 'Perhaps you meant "%s.curry"?' % name
