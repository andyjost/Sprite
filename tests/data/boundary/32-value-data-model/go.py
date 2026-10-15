'''
A Curry value as a Python object.  The node classes define a structural
equality and an identity hash, no order, and on the C++ backend no truth
and no length; indexing follows the successors of the node, so v[1] of a
list is its tail.  An evaluated expression node becomes a forward node that
topython does not follow, and curry.typed trusts its annotation.  The driver
is declared on the C++ backend: the Python backend gives bool(f) False,
len(n) 2 and <Int 2> for the evaluated node (P15, P16, P17).
'''
import os, curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
M = curry.import_('Model')
P = curry.import_('Prelude')

def vals(*goal, **kwds):
  return list(curry.eval(*goal, converter='topython', **kwds))

# Equal values hash apart, so a set keeps both; a node never equals a
# Python int (P15).
a, = curry.eval(M.inc, 41)
b, = curry.eval(M.inc, 41)
print('a == b ->', a == b)
print('hash(a) == hash(b) ->', hash(a) == hash(b))
print('len({a, b}) ->', len({a, b}))
print('a == 42 ->', a == 42)

# Values do not order; sorted needs a key.
coins = list(curry.eval(M.coin))
try:
  sorted(coins)
except TypeError as error:
  print('sorted(coins) !!', type(error).__name__)
print('sorted(coins, key=str) ->', sorted(coins, key=str))

# The node False is true in Python: the C++ node has no __bool__.
f, = curry.eval(getattr(P, 'not'), True)
print('(str(f), bool(f)) ->', (str(f), bool(f)))

# A list value has no len; n[0] is the head and n[1] the tail (P16).
n, = curry.eval([1, 2])
try:
  len(n)
except TypeError as error:
  print('len(n) !!', type(error).__name__)
print('n[0], n[1] ->', repr(n[0]), repr(n[1]))

# The evaluation rewrites the goal node in place: afterwards e is a forward
# node to the result.  The typed builder remembers the type of e, so a
# second evaluation works, but topython does not follow the forward (P17).
e = curry.expr(M.inc, 1)
print('e ->', repr(e))
print('vals(e) ->', vals(e))
print('e after ->', repr(e))
print('vals(e) again ->', vals(e))
print('topython(e) ->', repr(curry.topython(e)))

# curry.typed states a type and checks nothing (P22).
print('typeof(e) ->', curry.typeof(e))
print("typeof(typed(e, 'Bool')) ->", curry.typeof(curry.typed(e, 'Bool')))
