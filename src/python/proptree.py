'''
Implements a property tree.  Used for metadata.
'''
import collections

__all__ = ['proptree']
NODE_TYPES = {}
DELIMITER = '.'

class _TreeNode(object):
  '''
  Base class of property tree nodes; implements methods.  Derived classes
  should provide __slots__.
  '''
  __slots__ = ()
  def __repr__(self):
    return '[%s]' % ','.join(
        '%s=%s' % (slot, str(getattr(self, slot)))
            for slot in self.__slots__
      )
  def __iter__(self):
    return iter(self.__slots__)
  def __getattr__(self, attr):
    if not attr: return self
    for part in attr.split(DELIMITER):
      assert not (part.startswith('__') and part.endswith('__'))
      self = object.__getattribute__(self, part)
    return self
  def __setattr__(self, attr, value):
    parts = attr.split(DELIMITER)
    self = getattr(self, '.'.join(parts[:-1]))
    object.__setattr__(self, parts[-1], value)
  def __getitem__(self, key):
    try:
      return getattr(self, key)
    except AttributeError:
      raise KeyError(key)
  def __setitem__(self, key, value):
    try:
      setattr(self, key, value)
    except AttributeError:
      raise KeyError(key)
  def __contains__(self, key):
    try:
      getattr(self, key)
    except AttributeError:
      return False
    else:
      return True
  def get(self, key, default=None):
    try:
      return getattr(self, key)
    except AttributeError:
      return default
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
  if name not in NODE_TYPES:
    NODE_TYPES[name] = type('proptreenode_'+name, (_TreeNode,), {'__slots__': slots})
  obj = NODE_TYPES[name]()
  for slot in slots:
    setattr(obj, slot, _buildtree(data[slot]))
  return obj

def _error(key, part):
  raise TypeError("key '%s' cannot be created at '%s'" % (key, part))

def proptree(flat):
  '''
  Convert a dict into a property tree.

  The dictionary may contain dot-delimited keys.  It will be converted into a
  property tree consisting of nested objects whose members correspond to
  dictionary keys.

  For example, ``{'a.b':1, 'a.c':2, 'x':3}`` is converted into an object ``t``
  such that the expressions ``t.a.b``, ``t.a.c`` and ``t.x`` are bound to 1, 2,
  and 3, respectively.
  '''
  if not isinstance(flat, collections.Mapping):
    return flat
  tree = {}
  for k,v in flat.items():
    t = tree
    parts = k.split(DELIMITER)
    for part in parts[:-1]:
      if DELIMITER in t:
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

