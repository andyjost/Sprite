from ..exceptions import ModuleLookupError, PrerequisiteError
from .. import config
from . import _filenames
from ..tools.utility import make_exception
from ..utility import curryname, filesys, formatDocstring
import logging, os
from contextvars import ContextVar
from contextlib import contextmanager
from dataclasses import dataclass

__all__ = ['currentfile', 'import_path', 'imports_path', 'program_path']
logger = logging.getLogger(__name__)
SUBDIR = config.intermediate_subdir()

def reserved_module_names():
  from ..backends.cxx import curryrtbindings as curryrt
  return curryrt.builtin_module_names()

# Authorization belongs to one import/build job and its nested readers.
_loader_inputs = ContextVar('loader_inputs', default=None)


@contextmanager
def loader_inputs(records=None, interp=None):
  current = _loader_inputs.get()
  token = _loader_inputs.set(dict(records or {})) if current is None or records is not None else None
  try:
    active = _loader_inputs.get()
    for name in tuple(getattr(interp, 'modules', {})):
      generation = loaded_generation(name, interp)
      if generation is not None:
        active.update(generation.inputs)
    yield active
  finally:
    if token is not None:
      _loader_inputs.reset(token)


def with_loader_inputs(function):
  from functools import wraps
  @wraps(function)
  def wrapped(*args, **kwds):
    owner = getattr(args[0], 'interp', args[0]) if args else None
    with loader_inputs(interp=owner):
      return function(*args, **kwds)
  return wrapped


def is_loader_snapshot(modulename, filename, records=None):
  """Check installed origin and unchanged bytes in the job's authorization."""
  import hashlib
  try:
    source = os.path.realpath(_filenames.curryfilename(filename))
    records = _loader_inputs.get() if records is None else records
    record = (records or {}).get(source)
    if record is None:
      return False
    with open(source, 'rb') as stream:
      digest = hashlib.sha256(stream.read()).hexdigest()
    installed = config.installed_path(
        'curry', 'lib', modulename.replace('.', os.sep) + '.curry')
    with open(installed, 'rb') as stream:
      expected = hashlib.sha256(stream.read()).hexdigest()
    return record == dict(name=modulename, digest=digest,
        origin=os.path.realpath(installed)) and digest == expected
  except (OSError, ValueError):
    return False


def record_loader_input(modulename, filename, origin, records=None):
  """Authorize only copies of the installed source or its authorized copies."""
  import hashlib
  active = _loader_inputs.get()
  if active is None:
    return
  installed = config.installed_path(
      'curry', 'lib', modulename.replace('.', os.sep) + '.curry')
  try:
    if not (os.path.samefile(origin, installed) or
        is_loader_snapshot(modulename, origin, records=records)):
      return
    with open(filename, 'rb') as stream:
      digest = hashlib.sha256(stream.read()).hexdigest()
    active[os.path.realpath(filename)] = dict(name=modulename, digest=digest,
        origin=os.path.realpath(installed))
  except OSError:
    return


def reject_library_shadow(modulename, filename, interp):
  if interp is None or modulename not in reserved_module_names() \
      or _installed_library_file(filename):
    return
  if is_loader_snapshot(modulename, filename):
    return
  libraryfile = config.installed_path(
      'curry', 'lib', modulename.replace('.', os.sep) + '.curry')
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
  root = os.path.realpath(config.installed_path('curry', 'lib'))
  path = os.path.realpath(filename)
  return path == root or path.startswith(root + os.sep)

# Translation and execution share loaded names for the duration of a plan.
_translation_interp = ContextVar('translation_interp', default=None)


@contextmanager
def resolving(interp):
  token = _translation_interp.set(interp)
  try:
    yield
  finally:
    _translation_interp.reset(token)


def with_resolution(function):
  from functools import wraps
  @wraps(function)
  def wrapped(plan, *args, **kwds):
    from . import _frontend
    with loader_inputs(), resolving(getattr(plan, 'interp', plan)), _frontend.effective_imports():
      return function(plan, *args, **kwds)
  return wrapped


def loaded_source(name, interp=None):
  from ..objects import CurryPackage
  from ..objects.handle import getHandle
  interp = _translation_interp.get() if interp is None else interp
  module = getattr(interp, 'modules', {}).get(name)
  if module is not None and not isinstance(module, CurryPackage):
    raw = getattr(getHandle(module), 'icurry', None)
    filename = getattr(raw, 'filename', None)
    if filename:
      return _filenames.sourcefilename(filename)
  return None


@dataclass
class LoadedGeneration:
  source_info: object
  texts: dict
  source: object # real-path identity
  source_spelling: object # loaded source spelling, for sibling products
  image: object
  imports: tuple
  name: str
  object: object
  digests: dict
  inputs: dict

  def product_digest(self, kind):
    stem = os.path.splitext(_filenames.icurryfilename(self.source_spelling)
        if self.source_spelling else self.object)[0] if self.source_spelling or self.object else None
    if kind == 'image':
      path = self.image
    elif kind in ('object', 'cpp', 'stamp'):
      path = self.object or (stem + config.module_object_suffix() if stem else None)
      if path is None:
        return None
      if kind == 'cpp':
        path = os.path.splitext(path)[0] + '.cpp'
      elif kind == 'stamp':
        path += '.abi'
    else:
      path = stem + kind if stem else None
    return self.digests.get(os.path.realpath(path)) if path else None

  def acquire_object(self, path):
    from ..backends.cxx.image import digest
    self.object = path
    for product in (path, os.path.splitext(path)[0] + '.cpp', path + '.abi', path + '.imports'):
      self.digests[os.path.realpath(product)] = digest(product)


def loaded_generation(name, interp=None):
  from ..objects.handle import getHandle
  interp = _translation_interp.get() if interp is None else interp
  module = getattr(interp, 'modules', {}).get(name)
  from ..objects import CurryModule
  return getattr(getHandle(module).icurry, '_loaded_generation', None) \
      if isinstance(module, CurryModule) else None


def generation_for_source(source, interp=None):
  """Find a captured source by identity without reopening its header."""
  if source is None:
    return None
  interp = _translation_interp.get() if interp is None else interp
  for suffix in ('.imports', '.source', '.abi'):
    if source.endswith(suffix):
      source = source[:-len(suffix)]
  source = os.path.realpath(_filenames.sourcefilename(source))
  for name in tuple(getattr(interp, 'modules', {})):
    generation = loaded_generation(name, interp)
    if generation is not None and generation.source == source:
      return generation
  return None


def verify_product(generation, filename, identity=None):
  from ..backends.cxx.image import digest
  if digest(filename) != generation.digests.get(os.path.realpath(filename if identity is None else identity)):
    raise ValueError('the products of module %s changed since it was loaded; reload it'
        % generation.name)
  return filename


def verify_loaded_product(filename, interp=None, identity=None):
  """Check a disk input against the generation owned by this interpreter."""
  interp = _translation_interp.get() if interp is None else interp
  path = os.path.realpath(filename if identity is None else identity)
  for name in tuple(getattr(interp, 'modules', {})):
    generation = loaded_generation(name, interp)
    if generation is None:
      continue
    if generation.digests.get(path) is not None:
      verify_product(generation, filename, identity=path)
  return filename


def capture_generation(module, interp):
  """Pin source provenance and interfaces before publishing a loaded module."""
  from pathlib import Path
  from .. import cache
  from ..objects.handle import getHandle
  handle = getHandle(module)
  raw = handle.icurry
  objectfile = handle.sofilename
  if not raw.filename and not objectfile:
    return
  sourcefile = os.path.abspath(_filenames.sourcefilename(raw.filename)) if raw.filename else None
  source = os.path.realpath(sourcefile) if sourcefile else None
  # Source identity follows symlinks; products belong to the spelling loaded.
  stem = Path(_filenames.icurryfilename(sourcefile) if sourcefile else objectfile).with_suffix('')
  texts = {}
  for suffix in ('.fint', '.icurry', '.icy.imports', '.icy.source'):
    path = Path(str(stem) + suffix)
    key = {'.fint': 'all.fint', '.icurry': 'all.interface'}.get(suffix)
    embedded = raw.metadata.get(key) if key else None
    try:
      data = path.read_bytes()
    except OSError:
      data = None
    if embedded is not None:
      encoded = embedded.encode('utf-8')
      # Text metadata has universal newlines; retain the matching physical
      # spelling so later byte verification also works for CRLF products.
      texts[suffix] = data if data is not None and \
          data.replace(b'\r\n', b'\n') == encoded.replace(b'\r\n', b'\n') else encoded
    elif data is not None:
      texts[suffix] = data
  try:
    info = cache._sourceinfo(source) if source else None
  except OSError:
    info = None
  from ..backends.cxx import image
  provenance = getattr(raw, '_attached_image', None)
  if provenance is None and source is not None:
    candidate = os.path.splitext(objectfile)[0] + '.img' if objectfile else image.filename(sourcefile)
    provenance = candidate if os.path.isfile(candidate) else None
  products = [str(stem) + '.icy', str(stem) + '.img', provenance]
  diskobject = objectfile or str(stem) + config.module_object_suffix()
  products.extend((diskobject, os.path.splitext(diskobject)[0] + '.cpp', diskobject + '.abi', diskobject + '.imports'))
  digests = {os.path.realpath(path): image.digest(path) for path in products if path}
  import hashlib
  digests.update((os.path.realpath(str(stem) + suffix), hashlib.sha256(data).hexdigest())
      for suffix, data in texts.items())
  imports = tuple((name, loaded_generation(name, interp)) for name in raw.imports)
  raw._loaded_generation = LoadedGeneration(
      info, texts, source, sourcefile, provenance, imports, raw.fullname, objectfile, digests,
      dict(_loader_inputs.get() or {}))


def module_path(name, search):
  """Resolve a loaded generation first, otherwise preserve path order."""
  source = loaded_source(name)
  if source is None:
    return search
  from ._frontend import source_root
  return [source_root(source)]


def _modulefiles(plan, name, currypath):
  '''Files in path order, then namespace directories from the whole path.'''
  source = loaded_source(name, plan.interp)
  if source is not None and name not in reserved_module_names():
    for filename in reversed(plan.filelist(source)):
      if os.path.isfile(filename):
        yield filename
    return
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

def program_path(name, currypath, is_sourcefile=False, resolved_path=False, **ignored):
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
  if is_sourcefile and not resolved_path:
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

@with_resolution
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
  modulename = (_filenames.module_name(name) if is_sourcefile else
                curryname.getModuleName(name, False))
  currypath = program_path(name, currypath, is_sourcefile,
      resolved_path=ignored.get('resolved_path', False))
  # ICurry provenance needs the same effective import path as images and
  # objects, including imports by name whose imports_path is None.
  effective = import_path(plan.interp, imports_path(currypath, is_sourcefile)) \
      if plan.interp is not None else imports_path(currypath, is_sourcefile)
  if effective is None and plan.interp is not None:
    effective = plan.interp.path
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
  if os.path.isfile(curryfile):
    modulename = _filenames.module_name(curryfile)
  reject_library_shadow(modulename, curryfile, plan.interp)
  filelist = plan.filelist(curryfile)
  from . import _curry2icurry, _interfaces
  icyfile = _filenames.icurryfilename(curryfile)
  source_changed = os.path.isfile(curryfile) and not \
      _curry2icurry.source_matches(curryfile, icyfile)
  if plan.stages[0].step is _curry2icurry.curry2icurry \
      and (source_changed or (
          os.path.isfile(curryfile) and not os.path.isfile(icyfile)
          and not _interfaces.is_current(icyfile, effective))):
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
  if plan.interp is not None and plan.flags & plans.MAKE_ICURRY \
      and not source_changed and os.path.isfile(curryfile):
    # Refresh direct imports before judging their interfaces. Importing an
    # unchanged B must also see A's newly translated interface when A's
    # source changed but nobody has imported A yet.
    try:
      names = _interfaces.imports(icyfile) if os.path.isfile(icyfile) else \
          list(_interfaces.read(icyfile + _interfaces.SUFFIX) or {})
    except (OSError, ValueError):
      names = [] # the normal reader diagnoses a malformed ICurry file
    if not plan.flags & plans.MAKE_TARGET_SOURCE:
      # An ICurry-only build must refresh replacement interfaces too, but
      # planning a complete installed library must not load its modules.
      search = plan.interp.path if effective is None else effective
      names = [dep for dep in names
          for path in list(_modulefiles(plan, dep, search))[:1]
          if not _installed_library_file(path)]
    if names:
      plan.interp.import_(names, currypath=import_path(plan.interp,
          imports_path(currypath, is_sourcefile)))
    if os.path.isfile(curryfile) and not os.path.isfile(icyfile) \
        and not _interfaces.is_current(icyfile, effective):
      filelist = [curryfile]
  for product in filelist:
    verify_loaded_product(product, plan.interp)
  filelist = plan.prune_stale(filelist, effective)
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
