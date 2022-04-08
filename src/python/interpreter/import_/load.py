'''
Code to load runtime symbols.
'''

from ... import config, icurry, objects, utility
from ...utility import encoding, visitation
import collections, six, weakref

__all__ = ['loadSymbols']

@visitation.dispatch.on('idef')
def loadSymbols(interp, idef, moduleobj, **kwds): #pragma: no cover
  '''
  Load symbols (i.e., constructor and functions names) from the ICurry
  definition ``idef`` into module ``moduleobj``.
  '''
  raise RuntimeError("unhandled ICurry type during symbol loading: '%s'" % type(idef))

@loadSymbols.when(collections.Sequence, no=(str))
def loadSymbols(interp, seq, *args, **kwds):
  return [loadSymbols(interp, item, *args, **kwds) for item in seq]

@loadSymbols.when(collections.Mapping)
def loadSymbols(interp, mapping, moduleobj, **kwds):
  return {
      k: loadSymbols(interp, v, moduleobj, **kwds)
        for k,v in six.iteritems(mapping)
    }

@loadSymbols.when(icurry.IModule)
def loadSymbols(interp, imodule, moduleobj, **kwds):
  for modulename in imodule.imports:
    interp.import_(modulename)
  interp.optimize(imodule)
  loadSymbols(interp, imodule.types, moduleobj, **kwds)
  loadSymbols(interp, imodule.functions, moduleobj, **kwds)
  return moduleobj

@loadSymbols.when(icurry.IDataType)
def loadSymbols(interp, itype, moduleobj):
  dt_impl = interp.backend.materialize(interp, itype)
  cy_ctors = []
  for ictor, ctorinfo in zip(itype.constructors, dt_impl.constructors):
    cy_ctorobj = objects.CurryNodeInfo(ctorinfo, icurry=ictor, typename=itype.fullname)
    cy_ctors.append(cy_ctorobj)
    getattr(moduleobj, '.symbols')[cy_ctorobj.name] = cy_ctorobj
    if encoding.isaCurryIdentifier(cy_ctorobj.name):
      setattr(moduleobj, cy_ctorobj.name, cy_ctorobj)
  cy_dtobj = objects.CurryDataType(dt_impl, cy_ctors, icurry=itype)
  getattr(moduleobj, '.types')[cy_dtobj.name] = cy_dtobj
  return cy_dtobj

@loadSymbols.when(icurry.IFunction)
def loadSymbols(interp, ifun, moduleobj):
  info = interp.backend.materialize(interp, ifun)
  cy_fobj = objects.CurryNodeInfo(info, icurry=ifun)
  getattr(moduleobj, '.symbols')[cy_fobj.name] = cy_fobj
  if not ifun.is_private and encoding.isaCurryIdentifier(cy_fobj.name):
    setattr(moduleobj, cy_fobj.name, cy_fobj)
  return cy_fobj

