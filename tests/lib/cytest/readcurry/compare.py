from . import types
from itertools import izip_longest
import operator, re

__all__ = ['compare']

def compare(a, b):
  '''
  Compares Curry results with proper handling of variable names and value sets.
  '''
  comparefunc = SetValues() >> VariableRenaming()
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

class Comparison(object):
  def __init__(self, nextf=operator.eq):
    self.nextf = nextf
  def __rshift__(self, rhs):
    return type(self)(nextf=rhs)

class SetValues(Comparison):
  '''
  Compare SetFunctions.Values without regard to element order or multiplicity.
  '''
  def __call__(self, a, b):
    if all(
        isinstance(x, types.Applic) and x.f.name == 'Values'
        for x in [a, b]
      ):
      a, = map(set, a.args)
      b, = map(set, b.args)
    return self.nextf(a, b)

class VariableRenaming(Comparison):
  '''
  Compare modulo renaming of variables.
  '''
  def __init__(self):
    Comparison.__init__(self)
    self.freevar_map = {}

  def __call__(self, a, b):
    if self.nextf(a, b):
      return True
    if all(isinstance(x, types.Freevar) for x in (a,b)):
      self.freevar_map.setdefault(a.name, b.name)
      if self.freevar_map[a.name] == b.name:
        return True
    return False

