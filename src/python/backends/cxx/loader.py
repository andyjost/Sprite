from ...icurry import types as icurry_types
from ... import config, exceptions
from . import cyrtbindings as cyrt
import os

__all__ = ['load_module']

# The keys of the optimizer passes in the metadata of a module (see
# interpreter.optimize.default_optimizers).
OPTIMIZER_PREFIX = 'cxx.opt.'

def load_module(interp, sofile):
  assert sofile.endswith('.so')
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
  # The record names a source under the installation relative to SPRITE_HOME
  # (see compiler._source_file_name).
  filename = bom.filename
  if filename is not None and not os.path.isabs(filename):
    filename = config.installed_path(filename)
  imodule = icurry_types.IModule.fromBOM(
      fullname  = bom.fullname
    , imports   = bom.imports
    , types     = bom.types
    , functions = bom.functions
    , mdkey     = 'cxx.material'
    , filename  = filename
    , aliases   = bom.aliases
    , metadata  = metadata
    )
  return interp.import_(imodule)
