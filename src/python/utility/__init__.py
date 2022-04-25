import contextlib, sys

__all__ = ['formatDocstring', 'maxrecursion', 'translateKwds', 'unique']

# The recursive-descent processing of ICurry necessitates a larger recursion
# limit.  If it is see too large, true infinite recursion may cause a SEGV
# (depending on the process stack limit).  This value should be a compromise.
MAX_RECURSION_LIMIT = 1<<14

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

@contextlib.contextmanager
def maxrecursion(limit=MAX_RECURSION_LIMIT):
  prevlimit = sys.getrecursionlimit()
  try:
    sys.setrecursionlimit(limit)
    yield
  finally:
    sys.setrecursionlimit(prevlimit)

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
