from . import types
from ..utility.visitation import dispatch

@dispatch.on('arg')
def merge(arg, extern, **kwds):
  '''
  Merge metadata from an external module into an ICurry object

  Args:
    arg:
      An instance of IConstructor, IFunction or IDataType.
    extern:
      An instance of IModule that provides external definitions.  If provided,
      this takes precedence over the metadata found in arg.
    itype:
      Keyword only.  An instance of IDataType, used to resolve constructors.
      Required for IConstructor.
  '''
  assert False

@merge.when(types.IConstructor)
def merge(icons, extern, itype):
  if extern is not None and itype.name in extern.types:
    for ctor in extern.types[itype.name].constructors:
      if ctor.name == icons.name:
        icons.update_metadata(ctor.metadata)

@merge.when(types.IFunction)
def merge(ifun, extern):
  if extern is not None and ifun.name in extern.functions:
    ifun.update_metadata(extern.functions[ifun.name].metadata)

@merge.when(types.IDataType)
def merge(itype, extern):
  if extern is not None and itype.name in extern.types:
    itype.update_metadata(extern.types[itype.name].metadata)




