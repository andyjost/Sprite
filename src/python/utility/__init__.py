import os
import re

__all__ = ['formatDocstring', 'isLegalModulename', 'removeSuffix']

def formatDocstring(*args, **kwds):
  def decorator(f):
    f.__doc__ = f.__doc__.format(*args, **kwds)
    return f
  return decorator

g_ident = re.compile(r'[_a-zA-Z][_a-zA-Z0-9]*$')
def isLegalModulename(name):
  return all(re.match(g_ident, part) for part in name.split('.'))

def removeSuffix(name, suffix):
  if not name.endswith(suffix):
    raise ValueError('expected suffix "%s"' % suffix)
  return name[:-len(suffix)]
