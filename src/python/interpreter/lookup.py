from . import exceptions
from .. import icurry

def module(interp, name):
  '''Look up a module by name.'''
  iname = icurry.IName(name)
  try:
    return interp.modules[iname.module]
  except KeyError:
    raise exceptions.ModuleLookupError('module "%s" not found' % iname.module)

def symbol(interp, name):
  '''Look up a symbol by its fully-qualified name.'''
  return _symbol(interp.module(name), icurry.IName(name))

def _symbol(module, iname):
  '''Implementation of symbol lookup.'''
  symbols = getattr(module, '.symbols')
  try:
    return symbols[iname.basename]
  except KeyError:
    raise exceptions.SymbolLookupError(
        'module "%s" has no symbol "%s"' % (iname.module, iname.basename)
      )

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
