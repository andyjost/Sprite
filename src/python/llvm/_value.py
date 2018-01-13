# Pure-Python extensions for class value.

from ._llvm import value
from . import _utility

method = _utility.method(value)

@method
def __nonzero__(self):
  return self.id != 0

@method
def __eq__(self, rhs):
  return self.id == rhs.id

@method
def __ne__(self, rhs):
  return self.id != rhs.id

@method
def __lt__(self, rhs):
  return self.id < rhs.id

@method
def __gt__(self, rhs):
  return self.id > rhs.id

@method
def __le__(self, rhs):
  return self.id <= rhs.id

@method
def __ge__(self, rhs):
  return self.id >= rhs.id

