
def method(cls, name=None):
  '''Add the wrapped function to the specified class.'''
  def wrapper(f):
    setattr(cls, f.__name__ if name is None else name, f)
    return f
  return wrapper

