'''Implements CurryModule.'''

from . import exceptions
import os
import types

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


def symbol(moduleobj, iname):
  '''Look up the given symbol name in the module.'''
  symbols = getattr(moduleobj, '.symbols')
  try:
    return symbols[iname.basename]
  except KeyError:
    raise exceptions.SymbolLookupError(
        'module "%s" has no symbol "%s"' % (iname.module, iname.basename)
      )

def _getfile(moduleobj, suffix):
  if moduleobj.__file__:
    filename = os.path.join(
        os.path.dirname(moduleobj.__file__)
      , '.curry/_interactive_' + suffix
      )
    if os.path.exists(filename):
      return filename

def getreadable(moduleobj):
  '''
  Returns the file containing human-readable ICurry, if one exists, or None.
  '''
  return _getfile(moduleobj, '.read')

def getjson(moduleobj):
  '''Returns the file containing ICurry-JSON, if one exists, or None.'''
  return _getfile(moduleobj, '.json')

def geticurry(moduleobj):
  '''Gets the ICurry associated witha  module.'''
  return getattr(moduleobj, '.icurry')

