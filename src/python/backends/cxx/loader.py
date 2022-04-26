from ...icurry import types as icurry_types
from . import cyrtbindings as cyrt

__all__ = ['load_module']

def load_module(interp, sofile):
  assert sofile.endswith('.so')
  shlib = cyrt.SharedCurryModule(sofile)
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
