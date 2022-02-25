from ....common import T_CTOR, T_FUNC
from ....import objects
from .... import icurry

__all__ = ['materialize_function_info_stub', 'materialize_type']

def _nostep(*args, **kwds):
  pass

def _unreachable(*args, **kwds):
  assert False

def materialize_constructor_info(interp, itype, icons, moduleobj, extern):
  # For builtins, the 'all.tag' metadata contains the tag.
  builtin = 'all.tag' in icons.metadata
  metadata = icurry.metadata.getmd(icons, extern, itype=itype)
  InfoTable = interp.context.runtime.InfoTable
  info = InfoTable.create(
      moduleobj
    , icons.name
    , icons.arity
    , T_CTOR + icons.index if not builtin else metadata['all.tag']
    , _nostep if not builtin else _unreachable
    , getattr(metadata, 'py.format', None)
    , _gettypechecker(interp, metadata)
    , getattr(metadata, 'all.flags', 0)
    )
  return info

def materialize_function_info_stub(interp, ifun, moduleobj, extern):
  metadata = icurry.metadata.getmd(ifun, extern)
  InfoTable = interp.context.runtime.InfoTable
  info = InfoTable.create(
      getattr(moduleobj, '_handle', moduleobj)
    , ifun.name
    , ifun.arity
    , T_FUNC
    , None
    , getattr(metadata, 'py.format', None)
    , _gettypechecker(interp, metadata)
    , InfoTable.MONADIC if metadata.get('all.monadic') else 0
    )
  return info

def materialize_type(interp, itype, moduleobj, extern):
  '''
  Synthesize a type object, including its constructors.
  '''
  constructors = []
  for icons in itype.constructors:
    info = materialize_constructor_info(interp, itype, icons, moduleobj, extern)
    info_object = objects.CurryNodeInfo(icons, info)
    constructors.append(info_object)
  typedef = objects.CurryDataType(itype.name, constructors, moduleobj)
  for ctor in constructors:
    # ctor.info.typedef = weakref.ref(typedef)
    ctor.info.typedef = typedef
  return typedef

# FIXME: several things in the info table now have an interpreter bound.  It
# would be great to simplify that.  Maybe it should just be added as an entry
# to the info table.
def _gettypechecker(interp, metadata):
  '''
  If debugging is enabled, and a typechecker is defined, get it and bind the
  interpreter.
  '''
  if interp.flags['debug']:
    checker = getattr(metadata, 'py.typecheck', None)
    if checker is not None:
      return lambda *args: checker(interp, *args)
