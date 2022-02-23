
def lookup(modulename):
  if modulename == 'Prelude':
    from .prelude import PreludeSpecification
    return PreludeSpecification
  elif modulename == 'Control.SetFunctions':
    from .setfunctions import SetFunctionsSpecification
    return SetFunctionsSpecification

