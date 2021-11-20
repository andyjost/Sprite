# Pure-Python extensions for class symboltable.

from . import _utility
from ._llvm import symboltable
import collections as _coll
import six as _six

_coll.Mapping.register(symboltable)

method = _utility.method(symboltable)

@method
def keys(self):
  return list(_six.iterkeys(self))

@method
def values(self):
  return list(_six.itervalues(self))

@method
def items(self):
  return list(_six.iteritems(self))

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
  return str(dict(_six.iteritems(self)))

@method
def __repr__(self):
  return repr(dict(_six.iteritems(self)))

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

