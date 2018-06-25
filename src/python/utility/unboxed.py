class unboxed(object):
  '''Indicates that a literal passed to expr should remain unboxed.'''
  def __init__(self, value):
    self.value = value

