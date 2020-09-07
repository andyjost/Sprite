import re

def formatDocstring(*args, **kwds):
  def decorator(f):
    f.__doc__ = f.__doc__.format(*args, **kwds)
    return f
  return decorator

g_ident = re.compile('[_a-zA-Z][a-zA-Z0-9]*')
def isLegalModulename(name):
  return all(re.match(g_ident, part) for part in name.split('.'))

