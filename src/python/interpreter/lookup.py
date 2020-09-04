from .. import exceptions
from . import module as cymodule
from .. import icurry

def module(interp, name):
  '''Look up a module by name.'''
  iname = icurry.IName(name)
  try:
    return interp.modules[iname.module]
  except KeyError:
    raise exceptions.ModuleLookupError('Curry module "%s" not found' % iname.module)

def symbol(interp, name, modulename=None):
  '''Look up a symbol by its fully-qualified name, or relative to a module.'''
  return cymodule.symbol(module(interp, modulename or name), icurry.IName(name))

def type(interp, name):
  '''Returns the constructor info tables for the named type.'''
  module = interp.module(name)
  iname = icurry.IName(name)
  types = getattr(module, '.types')
  try:
    return types[iname.basename]
  except KeyError:
    raise exceptions.TypeLookupError(
        'module "%s" has no type "%s"' % (iname.module, iname.basename)
      )
