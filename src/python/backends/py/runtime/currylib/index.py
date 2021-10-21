
def lookup(modulename):
  if modulename == 'Prelude':
    from . import prelude
    return prelude
  elif modulename == 'Control.SetFunctions':
    from . import setfunctions
    return setfunctions

