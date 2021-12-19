'''Python bindings for libsprite.so.'''

from ._pybindings import *
import itertools, six
from six.moves import range

def Fingerprint__iter__(self):
  for i in range(self.capacity):
    v = self.get(i)
    if v != UNDETERMINED:
      yield i, v

def Fingerprint__repr__(self, limit=32):
  def parts():
    for i,v in self:
      yield "%s%s" % (i, 'L' if v == LEFT else 'R')
  body = list(itertools.islice(parts(), limit))
  if len(body) == limit:
    body += '...'
  return '<%s>' % ''.join(body)

def Fingerprint__reduce__(self):
  return Fingerprint, (), None, None, self.__iter__()

def Fingerprint__eq__(self, rhs):
  return all(a==b for a,b in six.moves.zip_longest(self, rhs))

def Fingerprint__ne__(self, rhs):
  return not (self == rhs)

def Fingerprint__le__(self, rhs):
  return all(i not in self or self.get(i) == lr for i,lr in rhs)

def Fingerprint__ge__(self, rhs):
  return rhs <= self

def Fingerprint__lt__(self, rhs):
  return self <= rhs and (self != rhs)

def Fingerprint__gt__(self, rhs):
  return rhs < self

def Fingerprint_consistentWith_(self, rhs):
  if self.depth < rhs.depth:
    return self < rhs
  else:
    return rhs < self

Fingerprint.__iter__ = Fingerprint__iter__
Fingerprint.__repr__ = Fingerprint__repr__
Fingerprint.__reduce__ = Fingerprint__reduce__
Fingerprint.__eq__ = Fingerprint__eq__
Fingerprint.__ne__ = Fingerprint__ne__
Fingerprint.__le__ = Fingerprint__le__
Fingerprint.__ge__ = Fingerprint__ge__
Fingerprint.__lt__ = Fingerprint__lt__
Fingerprint.__gt__ = Fingerprint__gt__
Fingerprint.consistentWith = Fingerprint_consistentWith_

