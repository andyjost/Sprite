from ...icurry import types as icurry_types
from ... import exceptions
from . import cyrtbindings as cyrt
import os

__all__ = ['load_module']

def load_module(interp, sofile):
  assert sofile.endswith('.so')
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
  imodule = icurry_types.IModule.fromBOM(
      fullname  = bom.fullname
    , imports   = bom.imports
    , types     = bom.types
    , functions = bom.functions
    , mdkey     = 'cxx.material'
    , filename  = bom.filename
    , aliases   = bom.aliases
    , metadata  = {'cxx.shlib': shlib}
    )
  return interp.import_(imodule)
