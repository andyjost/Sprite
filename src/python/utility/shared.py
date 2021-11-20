from copy import copy
import collections, six, sys

class Shared(object):
  '''
  Manages an object with copy-on-write semantics.  To access the contained
  object for reading or writing, use the ``read`` and ``write`` methods, resp.
  If the object has multiple references, then writing will trigger a copy.
  '''
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
  def __str__(self):
    return str(self.read)
  def __repr__(self):
    return str(self)
    return 'Shared(refcnt=%s, %s)' % (self.refcnt, self.obj)
  # Read-only container methods, for convenience.
  def __contains__(self, key):
    return key in self.obj
  def __len__(self):
    return len(self.obj)
  def __getitem__(self, key):
    return self.obj[key]
  def __iter__(self):
    return iter(self.obj)

class DefaultDict(collections.defaultdict):
  '''Like defaultdict but recursively copies values.'''
  def __copy__(self):
    return DefaultDict(self.default_factory, {k: copy(v) for k,v in six.iteritems(self)})
  copy = __copy__

def compose(typefunction, ty):
  '''
  Composes a type function and type.  The type function is a type, such as
  Shared or DefaultDict, that takes another type as its only argument.  The
  returned object has object-copy semantics.
  '''
  def factory(obj=None):
    if obj is None:
      return typefunction(ty)
    else:
      return copy(obj)
  return factory


