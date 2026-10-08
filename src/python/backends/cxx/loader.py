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

def needed_modules(sofile):
  '''
  The modules whose objects ``sofile`` needs, in the order of its NEEDED
  entries: the entries of the form of a SONAME of a compiled module
  (toolchain.soname).  The other entries, the runtime library and the
  system libraries, are left out.
  '''
  from . import toolchain
  names = []
  for entry in elf.read_dynamic(sofile).needed:
    name = toolchain.module_of_soname(entry)
    if name is not None:
      names.append(name)
  return names

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

def load_module(interp, sofile):
  assert sofile.endswith('.so')
  sofile = os.path.abspath(sofile)
  # The object names the objects of its imports by their SONAMEs, and the
  # dynamic linker satisfies such a name with an object of that name this
  # process has mapped: no search path leads to the file.  So the imports
  # are imported first, each from its object.  The plan imports them
  # before it accepts the object (Cpp2So.import_lacks_an_object); this
  # covers a load outside the plan (curry.load) and an object without its
  # generated file.  An import that runs without an object cannot satisfy
  # the name, so it is an error here, not a message of the dynamic linker.
  for modulename in needed_modules(sofile):
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
  # the first.  Its code would then come from the first file, so refuse it.
  registered = shlib.info.sofilename
  if os.path.realpath(registered) != os.path.realpath(sofile):
    raise exceptions.DynloadError(
        'cannot load module %r from %r: it is already loaded from %r'
      % (shlib.info.fullname, sofile, registered)
      )
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
