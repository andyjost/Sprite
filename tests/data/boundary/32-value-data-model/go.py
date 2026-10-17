'''
A Curry value as a Python object, on the public API.  The values of
the built-in types are Python data: an Int is an int, a Bool a bool, a list
a list, so equality, hash, order, truth, len and indexing are Python's.  A
term is typed when it is built and never changed by an evaluation;
curry.term(x, type=) unifies the annotation with the inferred type.
'''
import os
import curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
M = curry.import_('Model')
P = curry.import_('Prelude')

# Two values 42 are the int 42: equal, one hash, one member of a set.
a = curry.eval(M.inc(41)).one()
b = curry.eval(M.inc(41)).one()
print('a == b ->', a == b)
print('hash(a) == hash(b) ->', hash(a) == hash(b))
print('len({a, b}) ->', len({a, b}))
print('a == 42 ->', a == 42)

# Ints order.
coins = list(curry.eval(M.coin))
print('sorted(coins) ->', sorted(coins))
print('sorted(coins, key=str) ->', sorted(coins, key=str))

# The value False is the bool False.
f = curry.eval(P['not'](True)).one()
print('(str(f), bool(f)) ->', (str(f), bool(f)))

# A list value is a list.
n = curry.eval([1, 2]).one()
print('len(n) ->', len(n))
print('n[0], n[1] ->', repr(n[0]), repr(n[1]))

# A term is typed at the call and never changed by an evaluation.
e = M.inc(1)
print('e ->', repr(e))
print('list(eval(e)) ->', list(curry.eval(e)))
print('e after ->', repr(e))
print('list(eval(e)) again ->', list(curry.eval(e)))

# type= is unified with the inferred type.
print('typeof(e) ->', curry.typeof(e))
try:
  print("typeof(term(e, type='Bool')) ->", curry.typeof(curry.term(e, type='Bool')))
except curry.CurryTypeError as error:
  print("typeof(term(e, type='Bool')) !!", type(error).__name__ + ':', str(error).splitlines()[0])
