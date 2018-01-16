'''Implementation of the visitor pattern.'''
# See https://chris-lamb.co.uk/posts/visitor-pattern-in-python
import inspect
import operator

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
    '''
    if self._ordering is None:
      classes = self.handlers.keys()
      data = {
          cls: set(filter(lambda subcls: issubclass(subcls, cls), classes))
              for cls in classes
        }
      self._ordering = reduce(operator.add, map(list, toposort(data)), [])
    return self._ordering

  def __call__(self, *args, **kwds):
    try:
      bindings = inspect.getcallargs(self.default, *args, **kwds)
    except:
      target = self.default
    else:
      ty = type(bindings[self.selector])
      if ty in self.handlers:
        target = self.handlers[ty]
      else:
        for cls in self.ordering:
          if issubclass(ty, cls):
            target = self.handlers[cls]
            break
        else:
          target = self.default
    return target(*args, **kwds)

  def when(self, ty):
    def decorator(f):
      self.handlers[ty] = f
      self._ordering = None
      return self
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
      return Visitable(selector, default=f)
    return decorator

