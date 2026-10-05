'''
Code to load runtime symbols.
'''

from ... import config, icurry, objects, utility
from ...utility import encoding, visitation
import collections.abc, logging, weakref

logger = logging.getLogger(__name__)

__all__ = ['loadSymbols']

@visitation.dispatch.on('idef')
def loadSymbols(interp, idef, moduleobj, **kwds): #pragma: no cover
  '''
  Load symbols (i.e., constructor and functions names) from the ICurry
  definition ``idef`` into module ``moduleobj``.
  '''
  raise RuntimeError("unhandled ICurry type during symbol loading: '%s'" % type(idef))

@loadSymbols.when(collections.abc.Sequence, no=(str))
def loadSymbols(interp, seq, *args, **kwds):
  return [loadSymbols(interp, item, *args, **kwds) for item in seq]

@loadSymbols.when(collections.abc.Mapping)
def loadSymbols(interp, mapping, moduleobj, **kwds):
  return {
      k: loadSymbols(interp, v, moduleobj, **kwds)
        for k,v in mapping.items()
    }

@loadSymbols.when(icurry.IModule)
def loadSymbols(interp, imodule, moduleobj, **kwds):
  interp.optimize(imodule)
  loadSymbols(interp, imodule.types, moduleobj, **kwds)
  loadSymbols(interp, imodule.functions, moduleobj, **kwds)
  return moduleobj

@loadSymbols.when(icurry.IDataType)
def loadSymbols(interp, itype, moduleobj):
  dt_impl = interp.backend.materialize(interp, itype, moduleobj)
  assert dt_impl.name == itype.name
  cy_ctors = []
  for ictor, ctorinfo in zip(itype.constructors, dt_impl.constructors):
    cy_ctorobj = objects.CurryNodeInfo(
        ctorinfo, icurry=ictor, typename=itype.fullname, interp=interp
      , module=moduleobj
      )
    assert cy_ctorobj.name == ictor.name == ctorinfo.name
    cy_ctors.append(cy_ctorobj)
    getattr(moduleobj, '.symbols')[cy_ctorobj.name] = cy_ctorobj
    if encoding.isaCurryIdentifier(cy_ctorobj.name):
      setattr(moduleobj, cy_ctorobj.name, cy_ctorobj)
  cy_dtobj = objects.CurryDataType(dt_impl, cy_ctors, icurry=itype)
  getattr(moduleobj, '.types')[itype.name] = cy_dtobj
  return cy_dtobj

@loadSymbols.when(icurry.IFunction)
def loadSymbols(interp, ifun, moduleobj):
  info = interp.backend.materialize(interp, ifun, moduleobj)
  cy_fobj = objects.CurryNodeInfo(info, icurry=ifun, interp=interp, module=moduleobj)
  # The Prelude is not exempt: a primitive of the runtime that carried the
  # name of its Curry wrapper took the wrapper's place here once (the dated
  # TODO entry on the saturation of apply chains).
  assert cy_fobj.name == info.name == ifun.name, \
      (moduleobj.__name__, cy_fobj.name, info.name, ifun.name)
  getattr(moduleobj, '.symbols')[ifun.name] = cy_fobj
  if not ifun.is_private and encoding.isaCurryIdentifier(ifun.name):
    setattr(moduleobj, ifun.name, cy_fobj)
  return cy_fobj

