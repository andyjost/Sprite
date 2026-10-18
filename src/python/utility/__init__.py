import contextlib, os, sys

__all__ = ['cpu_count', 'formatDocstring', 'maxrecursion', 'translateKwds', 'unique']

# Extra room for the remaining recursive helpers.  This only changes the
# Python frame limit; C calls have separate, version-dependent guards.
# Structural walks use explicit stacks rather than relying on this limit.
MAX_RECURSION_LIMIT = 1<<14

def cpu_count():
  '''The cores this process may use, or one when the count is unknown.'''
  count = None
  if hasattr(os, 'process_cpu_count'):
    count = os.process_cpu_count()
  elif hasattr(os, 'sched_getaffinity'):
    try:
      count = len(os.sched_getaffinity(0))
    except OSError:
      pass
  return count or os.cpu_count() or 1

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
