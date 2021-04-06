'''Implements CurryModule.'''

from .. import config
from .. import exceptions
import os
import types

SUBDIR = config.intermediate_subdir()

# Note: artibrary symbols imported from Curry are added to Curry modules,
# risking name clashes.  Therefore, only hidden attributes are allowed here,
# and all must begin with a dot.  The exceptions are Python special names,
# which are unavoidable.
class CurryModule(types.ModuleType):
  '''A Python module for interfacing with a Curry module.'''
  def __new__(cls, imodule):
    self = types.ModuleType.__new__(cls, imodule.name)
    self.__file__ = imodule.filename
    setattr(self, '.icurry', imodule)
    setattr(self, '.symbols', {})
    setattr(self, '.types', {})
    return self

  def __init__(self, imodule):
    super(CurryModule, self).__init__(imodule.name)

  def __repr__(self):
    return "<curry module '%s'>" % self.__name__

  __str__ = __repr__


def symbol(moduleobj, name):
  '''Look up the given symbol name in the module.'''
  symbols = getattr(moduleobj, '.symbols')
  try:
    return symbols[name]
  except KeyError:
    raise exceptions.SymbolLookupError(
        'module "%s" has no symbol "%s"' % (moduleobj.__name__, name)
      )

def _getfile(moduleobj, suffixes):
  if moduleobj.__file__:
    for suffix in suffixes:
      filename = os.path.join(
          os.path.dirname(moduleobj.__file__)
        , '.curry'
        , SUBDIR
        , config.interactive_modname() + suffix
        )
      if os.path.exists(filename):
        return filename

def getjsonfile(moduleobj):
  '''Returns the file containing ICurry-JSON, if one exists, or None.'''
  return _getfile(moduleobj, ['.json', '.json.z'])

def geticurryfile(moduleobj):
  '''Gets the ICurry file associated with a module.'''
  return _getfile(moduleobj, ['.icy'])

def geticurry(moduleobj):
  '''Gets the ICurry associated with a module.'''
  return getattr(moduleobj, '.icurry')
