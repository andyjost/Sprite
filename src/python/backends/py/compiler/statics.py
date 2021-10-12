from .... import objects
from ....utility import encoding, visitation

__all__ = ['Closure', 'handle']

PX_TYPE = 'ty_' # typedef
PX_INFO = 'ni_' # node info
PX_FUNC = 'fn_' # external function
PX_DATA = 'va_' # values

class Closure(object):
  def __init__(self):
    # Bidirectional mapping:
    #     (category, object) <-> identifier
    self.data = {}

  @property
  def context(self):
    return {
        k:v[1] for k,v in self.data.items()
               if isinstance(k, str)
      }

  def insert(self, prefix, obj, name=None):
    '''
    Insert an object into the closure (if needed) and return its handle.

    Parameters:
    -----------
      ``prefix``
        A string that will be prepended to the handle name.

      ``obj``
        The object to place into the closure.

      ``name``
        An optional base name used to construct the handle.  By default, this
        is determined from the object by calling encoding.best.

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

  
  @visitation.dispatch.on('obj')
  def intern(self, obj):
    '''
    Internalize an object, selecting the prefix based on its type.  Returns the
    object handle.
    '''
    if callable(obj):
      # Note: since functions are incomparable, a function only matches if the
      # very same function object is pased in subsequent calls.
      return self.insert(PX_FUNC, obj)
    else:
      raise TypeError('cannot intern %r' % obj)

  @intern.when(objects.CurryNodeInfo)
  def intern(self, nodeinfo):
    return self.insert(PX_INFO, nodeinfo)

  @intern.when(objects.CurryDataType)
  def intern(self, typedef):
    return self.insert(PX_TYPE, typedef)
  
  @intern.when(tuple)
  def intern(self, values):
    assert all(isinstance(v, int) for v in values) or \
           all(isinstance(v, str) and len(v) in (1,2) for v in values) or \
           all(isinstance(v, float) for v in values)
    return self.insert(PX_DATA, values)

