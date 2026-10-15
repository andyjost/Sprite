'''
Nondeterministic operations driven from Python: choose, insert, permut and
three spellings of permutation sort, and double coin as call-time choice.

nondetfunc of PAKCS crosses the boundary by import.  Its rules overlap by
design, so the run script turns the warning of the front end off.  The
goals have no parameters; the operations permut, insert and sort are
applied to Python lists, which cross as Curry lists of Int.  The values of
a search come in the order of the scheduler under step mode; the driver
sorts the permutations so that the order of the output is fixed.
'''
import os, curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import nondetfunc as M

def vals(*goal):
  return list(curry.eval(*goal, converter='topython'))

def texts(*goal):
  return [str(v) for v in curry.eval(*goal)]

# goal1, goal2, goal3: permutation sort in three spellings, one value each.
print('goal1 ->', vals(M.goal1))
print('goal2 ->', vals(M.goal2))
print('goal3 ->', vals(M.goal3))

# goal4 = double coin, coin = o ? s o: two values and not three.  The
# argument of double is shared, so both occurrences of x are the same coin
# (call-time choice).  The constructors o and s are lower case; the pinned
# front end accepts them.
print('goal4 ->', texts(M.goal4))

# permut over a Python list: six permutations, sorted here for the output.
print('permut [1, 2, 3] ->', sorted(vals(M.permut, [1, 2, 3])))

# insert 0 [1, 2]: three positions.
print('insert 0 [1, 2] ->', sorted(vals(M.insert, 0, [1, 2])))

# sort over a Python list of four: the one sorted permutation.
print('sort [3, 1, 4, 2] ->', vals(M.sort, [3, 1, 4, 2]))

# choose applied from Python is a plain nondeterministic choice.
print('choose 1 2 ->', vals(M.choose, 1, 2))
