def format_docstring(*args, **kwds):
  def decorator(f):
    f.__doc__ = f.__doc__.format(*args, **kwds)
    return f
  return decorator
