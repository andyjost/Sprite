from ...exceptions import CompileError

__all__ = ['Flat2ICurryError']

class Flat2ICurryError(CompileError):
  '''An error in the translation from FlatCurry to ICurry.'''
  def __init__(self, message):
    Exception.__init__(self, message)
    self.report, self.line, self.column = message, None, None
