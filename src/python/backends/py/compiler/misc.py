__all__ = ['ExternallyDefined', 'IR']

class ExternallyDefined(Exception):
  '''
  Raised to indicate that a function is externally defined.  Provides the
  replacement.
  '''
  def __init__(self, ifun):
    self.ifun = ifun

class IR(object):
  def __init__(self, entry, lines, closure):
    self.closure = closure
    self.entry = entry
    self.lines = lines

