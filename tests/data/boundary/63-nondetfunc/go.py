'''
Nondeterministic operations driven from Python (the public API): choose,
insert, permut and three spellings of permutation sort, and double coin as
call-time choice.

nondetfunc of PAKCS crosses the boundary by import.  Its rules overlap by
design, so the run turns the warning of the front end off.  The goals have
no parameters; the operations permut, insert and sort are applied to Python
lists, which cross as Curry lists of Int, and the values come back as Python
lists.  The values of a search come in the order of the scheduler under step
mode; the driver sorts the permutations so that the order of the output is
fixed.
'''
import os
import curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
M = curry.import_('nondetfunc')

# goal1, goal2, goal3: permutation sort in three spellings, one value each.
print('goal1 ->', list(curry.eval(M.goal1)))
print('goal2 ->', list(curry.eval(M.goal2)))
print('goal3 ->', list(curry.eval(M.goal3)))

# goal4 = double coin, coin = o ? s o: two values and not three.  The
# argument of double is shared, so both occurrences of x are the same coin
# (call-time choice).  The constructors o and s are lower case; the pinned
# front end accepts them.
print('goal4 ->', [str(v) for v in curry.eval(M.goal4)])

# permut over a Python list: six permutations, sorted here for the output.
print('permut [1, 2, 3] ->', sorted(curry.eval(M.permut([1, 2, 3]))))

# insert 0 [1, 2]: three positions.
print('insert 0 [1, 2] ->', sorted(curry.eval(M.insert(0, [1, 2]))))

# sort over a Python list of four: the one sorted permutation.
print('sort [3, 1, 4, 2] ->', list(curry.eval(M.sort([3, 1, 4, 2]))))

# choose applied from Python is a plain nondeterministic choice.
print('choose 1 2 ->', list(curry.eval(M.choose(1, 2))))
