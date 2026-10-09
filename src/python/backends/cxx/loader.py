from ...icurry import types as icurry_types
from ...objects.handle import getHandle
from ...toolchain import _filenames
from ... import config, exceptions
from . import cyrtbindings as cyrt
from . import elf
import logging, os

logger = logging.getLogger(__name__)

__all__ = ['load_module', 'needed_modules', 'source_file']

# The keys of the optimizer passes in the metadata of a module (see
# interpreter.optimize.default_optimizers).
OPTIMIZER_PREFIX = 'cxx.opt.'

# The seconds a load waits for a background compile before it says so at
# the WARNING level (the first notice is at the INFO level).
WAIT_NOTICE_SECONDS = 5

def _dynamic_names(sofile):
  '''
  The names of modules in the dynamic section of ``sofile``, read without a
  load of the object: the full name of its own module, from its SONAME
  (toolchain.soname), or None for an object without one; and the modules
  whose objects it needs, in the order of its NEEDED entries, the entries of
  the form of a SONAME of a compiled module.  The other entries, the runtime
  library and the system libraries, are left out.
  '''
  from . import toolchain
  dynamic = elf.read_dynamic(sofile)
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
  Raises DynloadError when ``registered``, the file of the library loaded
  under the module name, is not ``sofile``: the runtime keeps one library per
  module name for as long as one is loaded.
  '''
  if os.path.realpath(registered) != os.path.realpath(sofile):
    raise exceptions.DynloadError(
        'cannot load module %r from %r: it is already loaded from %r'
      % (name, sofile, registered)
      )

def _check_before_open(interp, name, sofile):
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
  A module whose tables a shim names, and whose name no library is
  registered under, is refused: the module runs, or ran, interpreted in
  this process, and an object loaded now binds to its tables, which outlive
  the module.  The module in interp.modules does not decide it: after a
  reset the name is gone from there while the tables are kept, and a load
  then accepted left them pointing into the object once the new module
  released it (the next import of the name crashed).  A load of such an
  object would need the swap itself.
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
  registered = cyrt.SharedCurryModule.find_sofilename(name)
  if registered is not None:
    _refuse_other_file(name, registered, sofile)
  elif tiered.has_shim(name):
    raise exceptions.DynloadError(
        'cannot load module %r from %r: the module runs, or ran, '
        'interpreted in this process; load the object in a new process'
      % (name, sofile)
      )

def load_module(interp, sofile):
  assert sofile.endswith('.so')
  sofile = os.path.abspath(sofile)
  name, needed = _dynamic_names(sofile)
  if name is not None:
    _check_before_open(interp, name, sofile)
  # The object names the objects of its imports by their SONAMEs, and the
  # dynamic linker satisfies such a name with an object of that name this
  # process has mapped: no search path leads to the file.  So the imports
  # are imported first, each from its object.  The plan imports them
  # before it accepts the object (Cpp2So.import_lacks_an_object); this
  # covers a load outside the plan (curry.load) and an object without its
  # generated file.  An import that runs without an object cannot satisfy
  # the name, so it is an error here, not a message of the dynamic linker.
  for modulename in needed:
    module = interp.import_(modulename)
    if getHandle(module).sofilename is None:
      raise exceptions.DynloadError(
          'cannot load %r: its import %s runs without a compiled object'
        % (sofile, modulename)
        )
  # Under tiered execution the tables of the modules the interpreter runs
  # must be named before an object binds to them (see tiered.py).
  from . import tiered
  tiered.ensure_shims(interp)
  shlib = cyrt.SharedCurryModule(sofile)
  # The runtime keeps one registry entry per module name for as long as a
  # library of that name is loaded, and a second library joins the entry of
  # the first.  _check_before_open refused such a file before the open; this
  # is the backstop for an object without the SONAME of its module, whose
  # name is known only now.
  _refuse_other_file(shlib.info.fullname, shlib.info.sofilename, sofile)
  bom = shlib.bom
  # The metadata of the record carries the keys of the optimizer passes that
  # ran on the module, so no pass runs again on a module without bodies
  # (interpreter.optimize), as on the Python backend.  The merge key of the
  # built-ins stays behind: the merge adds the exported built-ins, which the
  # record does not list (toolchain.mergebuiltins).
  metadata = {
      key: value for key, value in bom.metadata.items()
                 if key.startswith(OPTIMIZER_PREFIX)
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
