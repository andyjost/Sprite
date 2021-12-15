from . import types
from ..utility.visitation import dispatch

@dispatch.on('arg')
def getmd(arg, extern, **kwds):
  '''
  Get metadata from an ICurry object

  Args:
    arg:
      An instance of IConstructor, IFunction or IDataType.
    extern:
      An instance of IModule that provides external definitions.  If provided,
      this takes precedence over the metadata found in arg.
    itype:
      Keyword only.  An instance of IDataType, used to resolve constructors.
      Required for IConstructor.

  Returns:
    The metadata value, if found, or None otherwise.
  '''
  assert False

@getmd.when(types.IConstructor)
def getmd(icons, extern, itype):
  if extern is not None and itype.name in extern.types:
    for ctor in extern.types[itype.name].constructors:
      if ctor.name == icons.name:
        return ctor.metadata
  return getattr(icons, 'metadata', None)

@getmd.when(types.IFunction)
def getmd(ifun, extern):
  if extern is not None and ifun.name in extern.functions:
    return extern.functions[ifun.name].metadata
  else:
    return getattr(ifun, 'metadata', None)

@getmd.when(types.IDataType)
def getmd(itype, extern):
  if extern is not None and itype.name in extern.types:
    return extern.types[itype.name].metadata
  else:
    return getattr(itype, 'metadata', None)

