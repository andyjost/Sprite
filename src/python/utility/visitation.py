'''Implementation of the visitor pattern.'''
# See https://chris-lamb.co.uk/posts/visitor-pattern-in-python
from __future__ import absolute_import
import functools, inspect, six
from six.moves import reduce

# From http://code.activestate.com/recipes/577413-topological-sort/
def toposort(data):
  for k, v in data.items():
    v.discard(k) # Ignore self dependencies
  extra_items_in_deps = reduce(set.union, data.values(), set()) - set(data.keys())
  data.update({item:set() for item in extra_items_in_deps})
  while True:
    ordered = set(item for item,dep in data.items() if not dep)
    if not ordered:
      break
    yield ordered
    data = {
        item: (dep - ordered)
            for item,dep in data.items()
            if item not in ordered
      }
  assert not data, "cyclic dependency in %r" % data

class Visitable(object):
  '''Implements the "accept" half of a visitor pattern.'''
  def __new__(cls, selector, default):
    self = object.__new__(cls)
    self.handlers = {}
    self._ordering = None
    self.default = default
    self.selector = selector
    return self

  @property
  def ordering(self):
    '''
    The ordering sorts classes by their (possibly abstract) subclass
    relationships.  This is used when no handler provides an exact match.
    Computing the ordering is O(n^2) w.r.t. the number of handlers.
    '''
    if self._ordering is None:
      classes = self.handlers.keys()
      data = {
          cls: set(filter(lambda subcls: issubclass(subcls, cls), classes))
              for cls in classes
        }
      self._ordering = [item for group in toposort(data) for item in group]
    return self._ordering

  def __call__(self, *args, **kwds):
    '''
    Visitor application.

    Finds the selector argument, gets its type, identifies the appropriate
    handler, and then dispatches the call to there.
    '''
    try:
      bindings = inspect.getcallargs(self.default, *args, **kwds)
    except:
      handler = self.default
    else:
      ty = type(bindings[self.selector])
      if ty in self.handlers:
        handler = self.handlers[ty]
      else:
        for cls in self.ordering:
          if issubclass(ty, cls):
            handler = self.handlers[cls]
            break
        else:
          handler = self.default
    return handler(*args, **kwds)

  def when(self, ty, replacement, no):
    if no is not None or isinstance(ty, tuple):
      ty = instance_checker(ty, no)
    def decorator(handler):
      self.handlers[ty] = handler
      self._ordering = None
      return replacement
    return decorator

class dispatch(object):
  '''
  Creates a new visitable function.  ``selector`` names the function parameter
  used for dispatch.
  '''
  @staticmethod
  def on(selector):
    def decorator(f):
      argspec = inspect.getargspec(f)
      if selector not in argspec.args and argspec.keywords is None:
        raise TypeError(
            "'%s' has no parameter '%s'" % (f.__name__, selector)
          )
      visitor = Visitable(selector, default=f)
      @functools.wraps(f)
      def replacement(*args, **kwds):
        return visitor(*args, **kwds)
      replacement.when = lambda ty,no=None: visitor.when(ty, replacement, no)
      return replacement
    return decorator

def instance_checker(yes=None, no=None):
  '''
  Builds a this-but-not-that instance checker class.

  The class returned is intended to be used with ``isinstance`` and
  ``issubclass``.  An object will be an instance of the returned class if it is
  an instance of ``yes`` but not an instance of ``no``.  Likewise for
  subclasses.  Either argument may be a tuple of classes.

  Identical calls to this function are guaranteed to return the same object, so
  the result may be used as a key.
  '''
  yes, no = (() if arg is None else arg for arg in [yes, no])
  memoized = instance_checker.__dict__.setdefault('_memoized', {})
  key = tuple(tuple(set(x if type(x) == tuple else [x])) for x in [yes,no])
  if key not in memoized:
    class __metaclass__(type):
      def __instancecheck__(self, obj):
        return isinstance(obj, yes) and not isinstance(obj, no)
      def __subclasscheck__(self, cls):
        return issubclass(cls, yes) and not issubclass(cls, no)
    class InstanceChecker(six.with_metaclass(__metaclass__)):
      pass
    memoized[key] = InstanceChecker
  return memoized[key]


