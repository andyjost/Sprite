
__all__ = ['formatDocstring', 'translateKwds', 'unique']

def formatDocstring(*args, **kwds):
  def decorator(arg):
    if isinstance(arg, type):
      ty = type.__new__(
          type(arg), arg.__name__, (arg,)
        , {'__doc__': arg.__doc__.format(*args, **kwds)}
        )
      ty.__module__ = arg.__module__
      return ty
    else:
      arg.__doc__ = arg.__doc__.format(*args, **kwds)
      return arg
  return decorator

def translateKwds(kwmap):
  '''
  For compatibility.  This decorator can be used to translate old argument
  names to new ones.
  '''
  def dec(f):
    def replacement(*args, **kwds):
      for name in kwmap:
        if name in kwds:
          kwds[kwmap[name]] = kwds.pop(name)
      return f(*args, **kwds)
    return replacement
  return dec

def unique(iterator, key=lambda x: x):
  '''Transform an iterator to filter out duplicate items.'''
  seen = set()
  for x in iterator:
    k = key(x)
    if k not in seen:
      seen.add(k)
      yield x
