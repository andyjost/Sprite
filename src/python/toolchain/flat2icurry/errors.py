from ...exceptions import CompileError

__all__ = ['Flat2ICurryError']

class Flat2ICurryError(CompileError):
  '''An error in the translation from FlatCurry to ICurry.'''
