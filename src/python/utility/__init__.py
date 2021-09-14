import os
import re
from ..exceptions import ModuleLookupError

__all__ = ['formatDocstring', 'isLegalModulename', 'removeSuffix', 'translateKwds']

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

g_ident = re.compile(r'[_a-zA-Z][_a-zA-Z0-9]*$')
def isLegalModulename(name):
  return all(re.match(g_ident, part) for part in name.split('.'))

def validateModulename(name):
  if not isLegalModulename(name):
    raise ModuleLookupError('%r is not a legal module name.' % name)

def removeSuffix(name, suffix):
  if not name.endswith(suffix):
    raise ValueError('expected suffix %r' % suffix)
  return name[:-len(suffix)]

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

