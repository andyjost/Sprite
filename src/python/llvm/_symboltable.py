# Pure-Python extensions for class symboltable.

from ._llvm import symboltable
from . import _utility
import collections as _coll

_coll.Mapping.register(symboltable)

method = _utility.method(symboltable)

@method
def keys(self):
  return list(self.iterkeys())

@method
def values(self):
  return list(self.itervalues())

@method
def items(self):
  return list(self.iteritems())

@method
def iterkeys(self):
  return iter(self)

@method
def itervalues(self):
  for key in self:
    yield self[key]

@method
def iteritems(self):
  for key in self:
    yield key, self[key]

@method
def __delitem__(self, name):
  self[name].erase()

@method
def __str__(self):
  return str(dict(self.iteritems()))

@method
def __repr__(self):
  return repr(dict(self.iteritems()))

@method
def __eq__(self, rhs):
  keys = self.keys()
  if keys != rhs.keys():
    return False
  for key in keys:
    if self[key].id != rhs[key].id:
      return False
  return True

@method
def __ne__(self, rhs):
  return not (self == rhs)

