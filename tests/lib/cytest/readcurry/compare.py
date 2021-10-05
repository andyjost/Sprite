from . import types
from itertools import izip_longest
import operator, re

__all__ = ['compare']

def compare(a, b, modulo_variable_renaming=False):
  comparefunc = EqualModuleVariableRenaming() if modulo_variable_renaming \
                                              else operator.eq
  return cmap(comparefunc, a, b)

def cmap(comparefunc, a, b):
  '''Maps a comparison function over Curry expressions.'''
  if type(a) != type(b):
    return False
  if isinstance(a, (list, tuple)):
    return reduce(
        lambda u,v: u and v
      , (comparefunc(u, v) for u,v in izip_longest(a, b))
      , True
      )
  else:
    return comparefunc(a, b)

class EqualModuleVariableRenaming(object):
  def __init__(self):
    self.freevar_map = {}

  def __call__(self, a, b):
    if a == b:
      return True
    if all(isinstance(x, types.Freevar) for x in (a,b)):
      self.freevar_map.setdefault(a.name, b.name)
      if self.freevar_map[a.name] == b.name:
        return True
    return False
