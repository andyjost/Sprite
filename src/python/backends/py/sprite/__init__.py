'''Python wrappers for libsprite.so.'''

from _sprite import *
import itertools

def Fingerprint__iter__(self):
  for i in xrange(self.capacity):
    v = self.get(i)
    if v != UNDETERMINED:
      yield i, v

def Fingerprint__repr__(self, limit=64):
  def chars():
    for i,v in self:
      for c in str(i):
        yield c
      yield 'L' if v == LEFT else 'R'
  return '<%s>' % ''.join(itertools.islice(chars(), limit))

Fingerprint.__iter__ = Fingerprint__iter__
Fingerprint.__repr__ = Fingerprint__repr__
