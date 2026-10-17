'''
Infinite lists consumed lazily from Python.

inflists and First of PAKCS cross the boundary by import.  A goal that takes
a prefix of an infinite list evaluates to a finite value.  Prelude.take
applied from Python to the infinite Curry list fibs takes fifteen Fibonacci
numbers.  First.goal2 narrows the free count x and the free start y of
first x (from y) =:= [O].  A Python iterator crosses the boundary as a lazy
Curry list: take 3 of itertools.count(10) ends after three elements and
never asks for a fourth.
'''
import os, itertools, curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import inflists, First
from curry.lib import Prelude as P

def vals(*goal):
  return list(curry.eval(curry.expr(*goal), converter='topython'))

def texts(*goal):
  return [str(v) for v in curry.eval(curry.expr(*goal), converter=None)]

# The three goals of inflists: ten Fibonacci numbers, five primes from the
# sieve, ten Hamming numbers.
print('goal1 ->', vals(inflists.goal1))
print('goal2 ->', vals(inflists.goal2))
print('goal3 ->', vals(inflists.goal3))

# Prelude.take from Python over the infinite list fibs of the module.
print('take 15 fibs ->', vals(P.take, 15, inflists.fibs))

# First.goal1 = first (S (S O)) (from O): the first two naturals.
print('First.goal1 ->', texts(First.goal1))

# First.goal2 x y: first x (from y) =:= [O] binds x to S O and y to O.
x, y = curry.free(), curry.free()
print('(First.goal2 x y, x, y) ->', texts(([First.goal2, x, y], x, y)))

# A Python iterator as the lazy list: only three elements are drawn.
counter = itertools.count(10)
print('take 3 (count 10) ->', vals(P.take, 3, counter))
print('next of the iterator ->', next(counter))
