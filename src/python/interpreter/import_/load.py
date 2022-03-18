'''
Code to load runtime symbols.
'''

from ... import config, icurry, objects, utility
from ...utility import encoding, visitation
import collections, six, weakref

__all__ = ['loadSymbols']

@visitation.dispatch.on('idef')
def loadSymbols(interp, idef, moduleobj, extern=None, **kwds): #pragma: no cover
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
def loadSymbols(interp, itype, moduleobj, extern=None):
  # FIXME: why does the frontend translate empty types to a type with one
  # constructor?  The check for _Constr# below might need to be adjusted.  It
  # should indicate the presence of a type that requires an external
  # definition.
  if not itype.constructors or \
      (len(itype.constructors) == 1 and \
       itype.constructors[0].name.startswith('_Constr#')):
    if extern is not None and itype.name in extern.types:
      itype.constructors = extern.types[itype.name].constructors
    else:
      raise ValueError(
          '%r has no constructors and no external definition was found.'
              % itype.fullname
        )
  assert itype.constructors
  be = interp.backend
  icurry.metadata.merge(itype, extern)
  dt_impl = be.materialize(interp, itype, extern)
  for ictor, ctorinfo in zip(itype.constructors, dt_impl.constructors):
    icurry.metadata.merge(ictor, extern, itype=itype)
    cy_ctorobj = objects.CurryNodeInfo(ctorinfo, icurry=ictor, typename=itype.fullname)
    _attachToModule(moduleobj, cy_ctorobj)
  cy_dtobj = objects.CurryDataType(dt_impl, icurry=itype)
  _attachToModule(moduleobj, cy_dtobj)
  return cy_dtobj

@loadSymbols.when(icurry.IFunction)
def loadSymbols(interp, ifun, moduleobj, extern=None):
  be = interp.backend
  icurry.metadata.merge(ifun, extern)
  info = be.materialize(interp, ifun, extern)
  cy_fobj = objects.CurryNodeInfo(info, icurry=ifun)
  _attachToModule(moduleobj, cy_fobj)
  return cy_fobj

@visitation.dispatch.on('obj')
def _attachToModule(moduleobj, obj, private=False):
  assert False

@_attachToModule.when(objects.CurryNodeInfo)
def _attachToModule(moduleobj, cy_infoobj, private=False):
  getattr(moduleobj, '.symbols')[cy_infoobj.name] = cy_infoobj
  if not private and encoding.isaCurryIdentifier(cy_infoobj.name):
    setattr(moduleobj, cy_infoobj.name, cy_infoobj)

@_attachToModule.when(objects.CurryDataType)
def _attachToModule(moduleobj, cy_dtobj, private=False):
  getattr(moduleobj, '.types')[cy_dtobj.name] = cy_dtobj

