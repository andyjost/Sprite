from . import types
from ..utility.visitation import dispatch

@dispatch.on('arg')
def merge(arg, extern, **kwds):
  '''
  Merge metadata from an external module into an ICurry object

  Args:
    arg:
      An instance of IFunction or IDataType.
    extern:
      An instance of IModule that provides external definitions.  If provided,
      this takes precedence over the metadata found in arg.
    itype:
      Keyword only.  An instance of IDataType, used to resolve constructors.
      Required for IConstructor.
  '''
  assert False

@merge.when(types.IFunction)
def merge(ifun, extern):
  if extern is not None and ifun.name in extern.functions:
    ifun.update_metadata(extern.functions[ifun.name].metadata)

@merge.when(types.IDataType)
def merge(itype, extern):
  if extern is not None and itype.name in extern.types:
    itype_extern = extern.types[itype.name]
    itype.update_metadata(itype_extern.metadata)
    for ictor, ictor_extern in zip(itype.constructors, itype_extern.constructors):
      ictor.update_metadata(ictor_extern.metadata)

