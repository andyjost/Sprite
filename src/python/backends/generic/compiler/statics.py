from ....icurry.types import IString
from .... import objects
from ....utility import encoding, strings, visitation
import six, sys

__all__ = ['Closure']

PX_DATA = 'da_' # data
PX_FUNC = 'fn_' # external function
PX_INFO = 'ni_' # node info
PX_STR  = 'st_' # string
PX_SYMB = 'cy_' # a Curry symbol
PX_TYPE = 'ty_' # typedef

NAME_LENGTH_LIMIT = 40

class Closure(object):
  def __init__(self):
    # Bidirectional mapping:
    #     (category, object) <-> identifier
    self.data = {}

  def __str__(self):
    from .. import render
    return '\n'.join(render.render(self))

  def triples(self):
    # Generates [(identifier, category, object)].
    for k,v in self.data.items():
      if isinstance(k, tuple):
        yield v, k[0], k[1]

  def find(self, obj):
    for item in self.triples():
      if obj in item:
        return item

  def nodeinfo(self, symbol):
    return self.data[PX_INFO, symbol]

  def typedefs(self):
    for name, cat, obj in self.triples():
      if cat == PX_TYPE:
        yield name, obj

  @property
  def dict(self):
    # Prepares a dictionary containing the name-object pairs of this closure.
    return {
        k:v[1] for k,v in self.data.items()
               if isinstance(k, str)
      }

  def insert(self, obj, name=None, prefix=''):
    '''
    Insert an object into the closure (if needed) and return its handle.

    Args:
      obj:
        The object to place into the closure.

      name:
        An optional base name used to construct the handle.  By default, this
        is determined from the object by calling encoding.best.

      prefix:
        A string that will be prepended to the handle name.

    Returns:
      A handle to the specified object.

    '''
    key = prefix, obj
    if key not in self.data:
      seed = obj if name is None else name
      handle = encoding.best(
          prefix, seed, disallow=self.data, limit=NAME_LENGTH_LIMIT
        )
      self.data[key] = handle
      self.data[handle] = key
    return self.data[key]

  def delete(self, handle):
    key = self.data[handle]
    assert key in self.data and handle in self.data
    del self.data[handle]
    del self.data[key]

  @visitation.dispatch.on('obj')
  def intern(self, obj):
    '''
    Internalize an object, selecting the prefix based on its type.  Returns the
    object handle.
    '''
    if callable(obj):
      # Note: since functions are incomparable, a function only matches if the
      # very same function object is pased in subsequent calls.  Furthermore,
      # only functions that can be imported relative to their module can be
      # used.
      if not importable(obj):
        raise TypeError(
            'cannot intern %r because it cannot be imported'
                % getattr(obj, '__name__', '<unknown>')
          )
      return self.insert(obj, prefix=PX_FUNC)
    else:
      raise TypeError('cannot intern %r' % obj)

  @intern.when(objects.CurryNodeInfo)
  def intern(self, nodeinfo):
    return self.insert(nodeinfo, prefix=PX_INFO)

  @intern.when(objects.CurryDataType)
  def intern(self, typedef):
    # assert isinstance(typedef, objects.CurryDataType)
    return self.insert(typedef, prefix=PX_TYPE)

  @intern.when(six.string_types)
  def intern(self, name):
    return self.insert(name, prefix=PX_SYMB)

  @intern.when(IString)
  def intern(self, istring):
    return self.insert(
        strings.ensure_binary(istring.value)
      , name=hex(hash(istring.value))[-6:]
      , prefix=PX_STR
      )

  @intern.when(tuple)
  def intern(self, values):
    assert all(isinstance(v, int) for v in values) or \
           all(isinstance(v, str) and len(v) in (1,2) for v in values) or \
           all(isinstance(v, float) for v in values)
    return self.insert(values, prefix=PX_DATA)

def importable(obj):
  modulename = getattr(obj, '__module__', None)
  name = getattr(obj, '__name__', None)
  module = sys.modules.get(modulename, None)
  found = getattr(module, name, None)
  return found is not None

def sortkey(item):
  name, value = item
  if name.startswith(PX_FUNC):
    return 1, value.__module__, value.__name__
  elif name.startswith(PX_INFO):
    return 2, value.fullname
  elif name.startswith(PX_TYPE):
    return 3, value.fullname
  elif name.startswith(PX_DATA):
    return 4, name
  else:
    return 5, name

