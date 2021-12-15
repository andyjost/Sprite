'''
Code to load runtime symbols.
'''

from ... import icurry, objects
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
  constructors = []
  constructors.extend(
      loadSymbols(
          interp, itype.constructors, moduleobj, extern, itype=itype
        )
    )
  typedef = objects.CurryDataType(itype.name, constructors, moduleobj)
  getattr(moduleobj, '.types')[itype.name] = typedef
  for i,ctor in enumerate(constructors):
    ctor.info.typedef = weakref.ref(typedef)
  return typedef

@loadSymbols.when(icurry.IConstructor)
def loadSymbols(interp, icons, moduleobj, extern=None, itype=None):
  cc = interp.context.compiler
  info = cc.synthesize_constructor_info(interp, itype, icons, extern)
  info_object = objects.CurryNodeInfo(icons, info)
  insertSymbol(moduleobj, icons.name, info_object)
  return info_object

@loadSymbols.when(icurry.IFunction)
def loadSymbols(interp, ifun, moduleobj, extern=None):
  cc = interp.context.compiler
  info = cc.synthesize_function_info_stub(interp, ifun, extern)
  info_object = objects.CurryNodeInfo(ifun, info)
  insertSymbol(moduleobj, ifun.name, info_object, ifun.is_private)
  return info_object


def insertSymbol(module, basename, nodeinfo, private=False):
  '''
  Inserts a symbol into the given module.

  All symbols are added to the module's '.symbols' dict.  Public symbols are
  also bound directly to the module itself.

  Args:
    module:
        An instance of ``CurryModule``.
    basename:
        A stirng containing the unqualified symbol name.
    nodeinfo:
        The nodeinfo for this symbol.
    private:
        Whether this is a private symbol.

  Returns:
    Nothing.
  '''
  getattr(module, '.symbols')[basename] = nodeinfo
  if not private and encoding.isaCurryIdentifier(basename):
    setattr(module, basename, nodeinfo)

