'''
Infinite lists consumed lazily from Python (the public API).

inflists and First of PAKCS cross the boundary by import.  A goal that takes
a prefix of an infinite list evaluates to a finite value.  Prelude.take
applied from Python to the infinite Curry list fibs takes fifteen Fibonacci
numbers.  First.goal2 narrows the free count x and the free start y of
first x (from y) =:= [O]; curry.solve reports the bindings.  A Python
iterator crosses the boundary as a lazy Curry list: take 3 of
itertools.count(10) ends after three elements and never asks for a fourth.
'''
import itertools, os
import curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
inflists, First = curry.import_('inflists'), curry.import_('First')
P = curry.import_('Prelude')

# The three goals of inflists: ten Fibonacci numbers, five primes from the
# sieve, ten Hamming numbers.
print('goal1 ->', list(curry.eval(inflists.goal1)))
print('goal2 ->', list(curry.eval(inflists.goal2)))
print('goal3 ->', list(curry.eval(inflists.goal3)))

# Prelude.take from Python over the infinite list fibs of the module.
print('take 15 fibs ->', list(curry.eval(P.take(15, inflists.fibs))))

# First.goal1 = first (S (S O)) (from O): the first two naturals.
print('First.goal1 ->', [str(v) for v in curry.eval(First.goal1)])

# First.goal2 x y: first x (from y) =:= [O] binds x to S O and y to O.
x, y = curry.free('x'), curry.free('y')
print('First.goal2 x y ->', [str(a) for a in curry.solve(First.goal2(x, y))])

# A Python iterator as the lazy list: only three elements are drawn.
counter = itertools.count(10)
print('take 3 (count 10) ->', list(curry.eval(P.take(3, counter))))
print('next of the iterator ->', next(counter))
