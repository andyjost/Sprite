# Permutation sort: a nondeterministic generator, a guard that fails the
# wrong candidates, and set functions that collect the survivors.
import os
import curry
curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import PermSort as S

xs = [3, 1, 2]
print(sorted(curry.eval(S.perm(xs))))         # six permutations, as values
print(curry.eval(S.sort(xs)).one())           # the one sorted permutation

# A set function returns a Values: a finite multiset, a Python collection.
v = curry.eval(S.permS(xs)).one()
print(type(v).__name__, len(v), sorted(v)[:2])
print(curry.eval(S.sortS([2, 1, 1])).one())   # two equal elements: a multiset

# Inside and outside.  A choice outside the capsule splits the result: one
# Values per outside alternative.  Nondeterminism inside stays inside.
for v in curry.eval(S.sortS(curry.choice([2, 1], [9, 8]))):
  print(v)
