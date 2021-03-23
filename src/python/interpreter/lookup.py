from .. import exceptions
from . import module as cymodule
from .. import icurry

def module(interp, name):
  '''Look up a module by name.'''
  try:
    return interp.modules[name]
  except KeyError:
    raise exceptions.ModuleLookupError('Curry module "%s" not found' % name)

def symbol(interp, name, modulename=None):
  '''
  Look up a symbol by its fully-qualified name or by its name relative to a
  module.
  '''
  if modulename is None:
    modulename, name = icurry.splitname(name)
  return cymodule.symbol(module(interp, modulename), name)

def type(interp, name):
  '''Returns the constructor info tables for the named type.'''
  modulename, typename = icurry.splitname(name)
  module = interp.module(modulename)
  types = getattr(module, '.types')
  try:
    return types[typename]
  except KeyError:
    raise exceptions.TypeLookupError(
        'module "%s" has no type "%s"' % (modulename, typename)
      )
