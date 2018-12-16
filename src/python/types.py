'''
Python types used to represent Curry types.
'''

class FreeType(object):
  '''
  The Python representation of free variable values.

  The assigned label (e.g., _a) is stored.
  '''
  def __init__(self, label):
    self.label = label

  def __eq__(self, rhs):
    return isinstance(rhs, FreeType) and self.label == rhs.label

  def __ne__(self, rhs):
    return not (self == rhs)

  def __repr__(self):
    return self.label

