from .shared import Shared

class UnionFind(object):
  '''Weighted quick-union with path compression.'''
  def __init__(self, obj=None):
    if obj is None:
      self.parent = Shared(dict)
      self.size = Shared(dict)
    else:
      self.parent = obj.parent.__copy__()
      self.size = obj.size.__copy__()
  def __copy__(self):
    return UnionFind(self)
  def __contains__(self, i):
    return i in self.parent.read
  def __getitem__(self, i):
    return self.parent.read.setdefault(i, i)
  def __setitem__(self, i, j):
    self.parent.write[i] = j
  def root(self, i):
    while i != self[i]:
      self[i] = self[self[i]]
      i = self[i]
    return i
  def find(self, p, q):
    return self.root(p) == self.root(q)
  def unite(self, p, q):
    i = self.root(p)
    j = self.root(q)
    if self.size.read.setdefault(i,1) < self.size.read.setdefault(j,1):
      self.parent.write[i] = j
      self.size.write[j] += self.size[i]
    else:
      self.parent.write[j] = i
      self.size.write[i] += self.size[j]
  def __repr__(self):
    return repr({k:v for k,v in self.parent.read.iteritems() if k!=v})

