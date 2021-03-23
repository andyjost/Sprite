from ..utility.visitation import dispatch
from .types import *

# @dispatch.on('arg')
# def unbox(arg):
#   '''Unapplies a built-in-type wrapper.'''
#   raise TypeError('expected an Applic')
# 
# @unbox.when(Applic)
# def unbox(applic):
#   if applic.ident not in ['Prelude.' + s for s in ['Int', 'Float', 'Char']]:
#     raise TypeError('expected an Int, Float, or Char')
#   assert len(applic.args) == 1
#   return applic.args[0]

@dispatch.on('arg')
def getmd(arg, extern, **kwds):
  '''
  Get metadata from an ICurry object

  Parameters:
  -----------
    ``arg``
      An instance of IConstructor, IFunction or IDataType.
    ``extern``
      An instance of IModule that provides external definitions.  If provided,
      this takes precedence over the metadata found in ``arg``.
    ``itype``
      Keyword only.  An instance of IDataType, used to resolve constructors.
      Required for IConstructor.

  Return:
  -------
  The metadata value, if found, or None otherwise.
  '''
  assert False

@getmd.when(IConstructor)
def getmd(icons, extern, itype):
  try:
    ctors = extern.types[itype.ident].constructors
    return next(c for c in ctors if c.ident == icons.ident).metadata
  except (AttributeError, KeyError, StopIteration):
    return getattr(icons, 'metadata', None)

@getmd.when(IFunction)
def getmd(ifun, extern):
  try:
    return extern.functions[ifun.ident].metadata
  except (AttributeError, KeyError):
    return getattr(ifun, 'metadata', None)

@getmd.when(IDataType)
def getmd(itype, extern):
  try:
    return extern.types[itype.ident].metadata
  except (AttributeError, KeyError):
    return getattr(itype, 'metadata', None)
