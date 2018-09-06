from copy import copy
import sys

class Shared(object):
  '''Manages an object with copy-on-write semantics.'''
  def __init__(self, ty, obj=None):
    self.ty = ty
    if obj is None:
      self.obj = ty()
      assert self.unique
    else:
      self.obj = obj
  def __copy__(self):
    return Shared(self.ty, self.obj) # sharing copy
  @property
  def read(self):
    return self.obj
  @property
  def write(self):
    if not self.unique:
      self.obj = self.ty(self.obj) # copy for write
    assert self.unique
    return self.obj
  @property
  def refcnt(self):
    return sys.getrefcount(self.obj) - 1
  @property
  def unique(self):
    return self.refcnt == 1
  def __repr__(self):
    return 'Shared(refcnt=%s, %s)' % (self.refcnt, self.obj)
  # Read-only container methods, for convenience.
  def __contains__(self, key):
    return key in self.obj
  def __len__(self):
    return len(self.obj)
  def __getitem__(self, key):
    return self.obj[key]

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
    return repr(self.parent.read)

