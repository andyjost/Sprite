from ..... import icurry
from .....common import T_CTOR, T_FUNC

def synthesize_constructor_info(interp, itype, icons, extern):
  # For builtins, the 'all.tag' metadata contains the tag.
  builtin = 'all.tag' in icons.metadata
  metadata = icurry.metadata.getmd(icons, extern, itype=itype)
  InfoTable = interp.context.runtime.InfoTable
  info = InfoTable(
      icons.name
    , icons.arity
    , T_CTOR + icons.index if not builtin else metadata['all.tag']
    , _nostep if not builtin else _unreachable
    , getattr(metadata, 'py.format', None)
    , _gettypechecker(interp, metadata)
    , getattr(metadata, 'all.flags', 0)
    )
  return info

def synthesize_function_info_stub(interp, ifun, extern):
  metadata = icurry.metadata.getmd(ifun, extern)
  InfoTable = interp.context.runtime.InfoTable
  info = InfoTable(
      ifun.name
    , ifun.arity
    , T_FUNC
    , None
    , getattr(metadata, 'py.format', None)
    , _gettypechecker(interp, metadata)
    , InfoTable.MONADIC if metadata.get('all.monadic') else 0
    )
  return info

def _nostep(*args, **kwds):
  pass

def _unreachable(*args, **kwds):
  assert False

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

