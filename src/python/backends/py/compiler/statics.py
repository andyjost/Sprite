from .... import objects
from ....utility import encoding, visitation
import sys

__all__ = ['Closure', 'handle']

PX_DATA = 'da_' # data
PX_FUNC = 'fn_' # external function
PX_INFO = 'ni_' # node info
PX_SYMB = 'cy_' # a Curry symbol
PX_TYPE = 'ty_' # typedef

class Closure(object):
  def __init__(self):
    # Bidirectional mapping:
    #     (category, object) <-> identifier
    self.data = {}

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

    Parameters:
    -----------
      ``obj``
        The object to place into the closure.

      ``name``
        An optional base name used to construct the handle.  By default, this
        is determined from the object by calling encoding.best.

      ``prefix``
        A string that will be prepended to the handle name.

    Returns:
    --------
      A handle to the specified object.

    '''
    key = prefix, obj
    if key not in self.data:
      handle = encoding.best(prefix, obj, disallow=self.data)
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
    return self.insert(typedef, prefix=PX_TYPE)

  @intern.when(str)
  def intern(self, name):
    return self.insert(name, prefix=PX_SYMB)

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
