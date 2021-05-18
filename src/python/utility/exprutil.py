'''Utilities for working with Curry expressions.'''

from .. import context

__all__ = ['iterexpr']

def iterexpr(expr):
  '''Generate each node in a Curry expression exactly once.'''
  queue = [expr]
  seen = set()
  while queue:
    x = queue.pop()
    if id(x) not in seen:
      seen.add(id(x))
      try:
        l = list(x)
      except TypeError:
        pass
      else:
        queue.extend(l)
      yield x

def maxid(expr):
  '''Returns the largest choice or variable ID in an expression.'''
  return reduce(
      max
    , (e[0] if isinstance(e, context.Node) and e.info.tag == T_CHOICE else -1
          for e in iterexpr(expr))
    , -1
    )

