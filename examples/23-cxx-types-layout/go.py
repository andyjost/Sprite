'''
Member layout by search over an algebraic model of C++ types.

Describes a struct in Python, lays it out in Curry after the Itanium ABI,
and searches the member order of the smallest size: once over every order,
and once with the first member fixed.

Usage: python go.py
'''
import os
import curry

# Find the shared modules under ../cxx, whatever the working directory is.
HERE = os.path.dirname(os.path.abspath(__file__))
curry.path.insert(0, os.path.join(HERE, '..', 'cxx'))
from curry.lib import CxxLimits, CxxType, CxxLayout

# The constructors of CxxType.Type, applied with curry.expr.
def fund(name):
  return curry.expr(CxxType.Fund, getattr(CxxLimits, name))

def const(t):
  return curry.expr(CxxType.Const, t)

def ptr(t):
  return curry.expr(CxxType.Ptr, t)

BOOL, CHAR, SHORT, INT, DOUBLE = (
    fund(name) for name in ('Bool', 'Char', 'Short', 'Int', 'Double')
  )

# The struct under study, as a reflection-like description.  The annotations
# of the class are its members in declaration order, each with its type, as
# the reflection of a compiler would list them.
class Packet:
  tag: CHAR
  stamp: DOUBLE
  urgent: BOOL
  length: INT
  port: SHORT
  payload: ptr(const(CHAR))

def members(struct):
  '''The members of a struct as a list of (name, type) pairs.  A name is
  passed as a list of characters: a str of length one would become a Char.'''
  return [(list(name), ty) for name, ty in struct.__annotations__.items()]

def value(goal, *args):
  '''The one value of a goal, converted to Python.'''
  return next(curry.eval(goal, *args, converter='topython'))

def show(t):
  '''A type in C++ syntax, printed by CxxType.showCxx.'''
  return value(CxxType.showCxx, t)

def print_layout(struct, lay):
  '''Prints a layout as a table: one row per member and one per hole.'''
  placed, size, align, tail = lay
  types = struct.__annotations__
  width = max([len(show(t)) for t in types.values()], default=0)
  print('  offset  size  member')
  for name, offset, bytes, pad in placed:
    if pad:
      print('  %6d  %4d  (padding)' % (offset - pad, pad))
    print('  %6d  %4d  %-*s  %s'
          % (offset, bytes, width, show(types[name]), name))
  if tail:
    print('  %6d  %4d  (padding)' % (size - tail, tail))
  print('  sizeof %d, alignof %d, padding %d'
        % (size, align, value(CxxLayout.padding, lay)))

def print_search(struct, search):
  '''Prints the result of a search: the counts, the order, and its layout.'''
  searched, reaching, lay = search
  placed, size, _, _ = lay
  print('  smallest sizeof %d, reached by %d of %d orders'
        % (size, reaching, searched))
  print('  the first of those orders: %s'
        % ', '.join(name for name, _, _, _ in placed))
  print_layout(struct, lay)

def main():
  struct = Packet
  ms = members(struct)
  # (a) The layout in declaration order.
  print('(a) struct %s in declaration order' % struct.__name__)
  print_layout(struct, value(CxxLayout.layout, ms))
  # (b) The order of the smallest size, over every order.
  print('(b) the order of the smallest size')
  print_search(struct, value(CxxLayout.smallest, ms))
  # (c) The same search with one more rule: the member declared first stays
  # first.
  first = list(struct.__annotations__)[0]
  print('(c) the order of the smallest size with %s first' % first)
  print_search(struct, value(CxxLayout.smallestWithFirst, list(first), ms))

if __name__ == '__main__':
  main()
