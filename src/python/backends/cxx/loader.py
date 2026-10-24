from ...icurry import types as icurry_types
from ...objects.handle import getHandle
from ...toolchain import _filenames
from ... import config, exceptions
from . import curryrtbindings as curryrt
from . import elf, macho
from ...utility.locking import native_metadata
import hashlib, logging, os

logger = logging.getLogger(__name__)
_objects = {}

__all__ = ['load_module', 'needed_modules', 'read_dynamic', 'source_file']

# The keys of the optimizer passes in the metadata of a module (see
# interpreter.optimize.default_optimizers).
OPTIMIZER_PREFIX = 'cxx.opt.'

# The seconds a load waits for a background compile before it says so at
# the WARNING level (the first notice is at the INFO level).
WAIT_NOTICE_SECONDS = 5

def read_dynamic(sofile):
  '''
  The dynamic section of the object ``sofile`` (elf.DynamicSection), read by
  the reader of its format: ELF, or Mach-O on macOS, where the install name
  stands as the SONAME and the loaded libraries as the needed names.  The
  format is told by the first bytes of the file.

  Raises:
    ValueError: the file is of neither format, or malformed.
  '''
  with open(sofile, 'rb') as stream:
    magic = stream.read(4)
  if magic == b'\x7fELF':
    return elf.read_dynamic(sofile)
  if magic in macho.MAGICS or magic in macho.MAGIC_32 or magic in macho.MAGIC_FAT:
    return macho.read_dynamic(sofile)
  raise ValueError('%r is neither an ELF nor a Mach-O file' % sofile)

def _dynamic_names(sofile):
  '''
  The names of modules in the dynamic section of ``sofile``, read without a
  load of the object: the full name of its own module, from its SONAME
  (toolchain.soname; the install name of a Mach-O object), or None for an
  object without one; and the modules whose objects it needs, in the order
  of its NEEDED entries (the loaded libraries of a Mach-O object), the
  entries of the form of a SONAME of a compiled module.  The other entries,
  the runtime library and the system libraries, are left out.
  '''
  from . import toolchain
  dynamic = read_dynamic(sofile)
  name = None if dynamic.soname is None \
      else toolchain.module_of_soname(dynamic.soname)
  needed = []
  for entry in dynamic.needed:
    modulename = toolchain.module_of_soname(entry)
    if modulename is not None:
      needed.append(modulename)
  return name, needed

def needed_modules(sofile):
  '''
  The modules whose objects ``sofile`` needs, in the order of its NEEDED
  entries (see _dynamic_names).
  '''
  return _dynamic_names(sofile)[1]

def source_file(record, sofile):
  '''
  The source file that the record of the module of ``sofile`` names (see
  compiler._source_file_name), as a path: a record that begins with a
  parent or current directory reference is relative to the directory of
  the object; another relative record is relative to the installation; an
  absolute record is a path as it is.  None for an empty record.

  An object-relative record counts on the layout of the toolchain: the
  object lies in the product directory beside its source
  (.curry/<subdir>/M.so beside M.curry; _filenames.curryfilename).  For an
  object elsewhere (a file of curry.save compiled in another directory)
  the record names no file of the module, so the result is None, and the
  module has no source file rather than a wrong one.
  '''
  if not record:
    return None
  if os.path.isabs(record):
    return record
  if record.startswith((os.pardir + os.sep, os.curdir + os.sep)):
    sofile = os.path.abspath(sofile)
    try:
      _filenames.curryfilename(sofile)
    except ValueError:
      logger.debug(
          'The record %r of %r is not resolved: the object does not lie in '
          'the product directory of its source'
        , record, sofile
        )
      return None
    return os.path.normpath(os.path.join(os.path.dirname(sofile), record))
  return config.installed_path(record)

def _refuse_other_file(name, registered, sofile):
  '''
  Raises LoadError when ``registered``, the file of the library loaded
  under the module name, is not ``sofile``: the runtime keeps one library per
  module name for as long as one is loaded.
  '''
  if os.path.realpath(registered) != os.path.realpath(sofile):
    raise exceptions.LoadError(
        'cannot load module %r from %r: it is already loaded from %r'
      % (name, sofile, registered)
      )

def _wait_pending(interp, name, sofile):
  '''
  The checks that precede the open of the object of module ``name``.

  An open writes tables: the dynamic initializers of the object construct
  its tables at the addresses its symbols resolve to, which the dynamic
  linker binds to the first definition in the global scope.  That is the
  table of a library of the name loaded already, or the live table of an
  interpreted module through its shim (tiered.py).  A refusal after the open
  dropped the object, and the tables it wrote pointed into unmapped memory:
  the next use, or the exit of the process, crashed (issue #109).  So the
  decision is taken here, from the registry of the runtime
  (SharedCurryModule.find_sofilename) and the state of tiered execution,
  before any dlopen.  A pending background compile of the module is waited
  for first, whatever the registry says (after a reset the registry may name
  the kept library of an earlier incarnation while the module runs
  interpreted again), and the object the compile wrote is the one loaded.
  An object of a module whose tables a shim names is adopted through the
  tiered swap, which keeps the object with those tables.  All refusals
  precede the open, including the checks of the shim in prepare_adoption.
  '''
  from . import tiered
  if tiered.pending(name):
    logger.info(
        'Waiting for the background compile of module %s before the load '
        'of %r', name, sofile
      )
    if not tiered.wait_for(name, timeout=WAIT_NOTICE_SECONDS, interp=interp):
      logger.warning(
          'still waiting for the background compile of module %s before the '
          'load of %r (the compile has run for more than %d s; Ctrl-C '
          'interrupts the wait)', name, sofile, WAIT_NOTICE_SECONDS
        )
      tiered.wait_for(name, interp=interp)
def _check_before_open(interp, name, sofile, from_plan=False):
  _wait_pending(interp, name, sofile)
  registered = curryrt.SharedCurryModule.find_sofilename(name)
  if registered is not None:
    _refuse_other_file(name, registered, sofile)

def _program_path(interp, sofile):
  '''
  The search path of the imports of the object ``sofile``: the directory
  of its source first, when the object lies in the product directory of a
  source (``_filenames.curryfilename``), then the path of the interpreter;
  None, the path of the interpreter alone, for an object elsewhere.
  '''
  from ...toolchain import _findcurry
  try:
    curryfile = _filenames.curryfilename(sofile)
  except ValueError:
    return None
  return _findcurry.program_path(curryfile, interp.path, is_sourcefile=True)

def load_module(interp, sofile, from_plan=False, fresh=False):
  while True:
    module = _load_module_once(interp, sofile, from_plan, fresh)
    if module is not None:
      return module


def _load_module_once(interp, sofile, from_plan, fresh):
  assert sofile.endswith('.so')
  sofile = os.path.abspath(sofile)
  from .toolchain import Cpp2So
  before = Cpp2So.product_snapshot(sofile)
  name, needed = _dynamic_names(sofile)
  from . import tiered
  if interp.flags['interpret'] == 'all':
    raise exceptions.LoadError(
        'cannot load %r under interpret:all: opening a compiled object '
        'replaces the live interpreted steps' % sofile
      )
  if name is not None:
    _wait_pending(interp, name, sofile)
  # The object names the objects of its imports by their SONAMEs, and the
  # dynamic linker satisfies such a name with an object of that name this
  # process has mapped: no search path leads to the file.  So the imports
  # are imported first, each from its object.  The plan imports them
  # before it accepts the object (Cpp2So.import_lacks_an_object); this
  # covers a load outside the plan (curry.load) and an object without its
  # generated file.  An import that runs without an object cannot satisfy
  # the name, so it is an error here, not a message of the dynamic linker.
  # The imports are searched beside the source of the object first, as the
  # imports of a program given as a file are (_findcurry.program_path).
  currypath = _program_path(interp, sofile)
  for modulename in needed:
    module = interp.import_(modulename, currypath=currypath)
    if getHandle(module).sofilename is None:
      raise exceptions.LoadError(
          'cannot load %r: its import %s runs without a compiled object'
        % (sofile, modulename)
        )
  # Under tiered execution the tables of the modules the interpreter runs
  # must be named before an object binds to them (see tiered.py).
  tiered.ensure_shims(interp)
  if before != Cpp2So.product_snapshot(sofile):
    return None # a producer published while dependencies were imported
  return _open_module(interp, sofile, name, from_plan, fresh, before)

@native_metadata
def _open_module(interp, sofile, name, from_plan, fresh, before):
  from . import tiered
  from .toolchain import Cpp2So
  if before != Cpp2So.product_snapshot(sofile):
    return None
  previous = None if name is None else curryrt.SharedCurryModule.find_sofilename(name)
  with open(sofile, 'rb') as stream:
    digest = hashlib.sha256(stream.read()).hexdigest()
  replace = previous is not None and name not in interp.modules \
      and (from_plan or fresh) and _objects.get(name) != (sofile, digest)
  if name is not None and not replace:
    registered = curryrt.SharedCurryModule.find_sofilename(name)
    if registered is not None:
      _refuse_other_file(name, registered, sofile)
  module = interp.modules.get(name)
  registered = curryrt.SharedCurryModule.find_sofilename(name) if name else None
  adopt = replace or (tiered.has_shim(name) and registered is None) or (
      module is not None and getHandle(module).sofilename is None
    )
  steps = tiered.prepare_adoption(interp, name) if adopt else []
  tiered.ensure_shims(interp)
  if adopt:
    owner = curryrt.Module.find_or_create(name)
    result = curryrt.tiered_adopt(name, [], sofile, steps)
    if not result['ok']:
      raise exceptions.LoadError('cannot load %r: %s' % (sofile, result['error']))
    shlib = owner.shlib
    tiered._refresh(name, interp)
  else:
    shlib = curryrt.SharedCurryModule(sofile)
  # The runtime keeps one registry entry per module name for as long as a
  # library of that name is loaded, and a second library joins the entry of
  # the first.  _check_before_open refused such a file before the open; this
  # is the backstop for an object without the SONAME of its module, whose
  # name is known only now.
  _refuse_other_file(shlib.info.fullname, shlib.info.sofilename, sofile)
  _objects[name] = sofile, digest
  bom = shlib.bom
  # The metadata of the record carries the keys of the optimizer passes that
  # ran on the module, so no pass runs again on a module without bodies
  # (interpreter.optimize), as on the former runtime.  The merge key of the
  # built-ins stays behind: the merge adds the exported built-ins, which the
  # record does not list (toolchain.mergebuiltins).
  metadata = {
      key: value for key, value in bom.metadata.items()
                 if key.startswith(OPTIMIZER_PREFIX) or key in ('all.fint', 'all.interface')
    }
  metadata['cxx.shlib'] = shlib
  imodule = icurry_types.IModule.fromBOM(
      fullname  = bom.fullname
    , imports   = bom.imports
    , types     = bom.types
    , functions = bom.functions
    , mdkey     = 'cxx.material'
    , filename  = source_file(bom.filename, sofile)
    , aliases   = bom.aliases
    , metadata  = metadata
    )
  return interp.import_(imodule)
