'''
Implements a property tree.  Used for metadata.
'''
import collections

__all__ = ['proptree']

_types_ = {}

class _TreeNode(object):
  __slots__ = ()
  def __repr__(self):
    return '[%s]' % ','.join(
        '%s=%s' % (slot, str(getattr(self, slot)))
            for slot in self.__slots__
      )
  def __contains__(self, key):
    return key in self.__slots__
  def __iter__(self):
    return iter(self.__slots__)
  def __getitem__(self, key):
    assert not (key.startswith('__') and key.endswith('__'))
    return getattr(self, key)
  def __setitem__(self, key, value):
    assert not (key.startswith('__') and key.endswith('__'))
    return setattr(self, key, value)
  def __eq__(self, rhs):
    return all(k==l and self[k]==rhs[k] for k,l in zip(self,rhs))

  def __ne__(self, rhs):
    return not (self == rhs)
  def __lt__(self, rhs): return NotImplemented
  def __gt__(self, rhs): return NotImplemented
  def __le__(self, rhs): return NotImplemented
  def __ge__(self, rhs): return NotImplemented

def _buildtree(data):
  # Return non-aggregate data.
  if not isinstance(data, collections.Mapping):
    return data

  # Build a property tree node from mappings.
  slots = tuple(sorted(data.keys()))
  name = '_'.join(slots)
  if name not in _types_:
    _types_[name] = type('proptreenode_'+name, (_TreeNode,), {'__slots__': slots})
  obj = _types_[name]()
  for slot in slots:
    setattr(obj, slot, _buildtree(data[slot]))
  return obj

def _error(key, part):
  raise TypeError("Key '%s' cannot be created at '%s'" % (key, part))

def proptree(flat, delim='.'):
  '''
  Convert a dict into a property tree.

  The dictionary may contain delimited keys.  It will be converted into a
  property tree consisting of nested objects whose members correspond to
  dictionary keys.

  For example, ``{'a.b':1, 'a.c':2, 'x':3}`` is converted into an object ``t``
  such that the expressions ``t.a.b``, ``t.a.c`` and ``t.x`` are bound to 1, 2,
  and 3, respectively.
  '''
  tree = {}
  for k,v in flat.items():
    t = tree
    parts = k.split(delim)
    for part in parts[:-1]:
      if delim in t:
        return _error(k, part)
      t = t.setdefault(part, {})
    part = parts[-1]
    try:
      if part in t: # may raise
        _error(k, part)
      t[part] = v
    except TypeError:
      _error(k, part)
  return _buildtree(tree)

