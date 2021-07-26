'''Python wrappers for libsprite.so.'''

from _sprite import *
import itertools

def Fingerprint__iter__(self):
  for i in xrange(self.capacity):
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

Fingerprint.__iter__ = Fingerprint__iter__
Fingerprint.__repr__ = Fingerprint__repr__
