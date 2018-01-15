'''Implementation of the visitor pattern.'''
# See https://chris-lamb.co.uk/posts/visitor-pattern-in-python
import inspect

class Visitable(object):
  '''Implements the "accept" half of a visitor pattern.'''
  def __new__(cls, selector, default):
    self = object.__new__(cls)
    self.cases = {}
    self.default = default
    self.selector = selector
    return self

  def __call__(self, *args, **kwds):
    try:
      bindings = inspect.getcallargs(self.default, *args, **kwds)
    except:
      target = self.default
    else:
      ty = type(bindings[self.selector])
      target = self.cases.get(ty, self.default)
    return target(*args, **kwds)

  def when(self, ty):
    def decorator(f):
      self.cases[ty] = f
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

