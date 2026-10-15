'''
Narrowing by inversion, driven from Python.

Three programs of PAKCS cross the boundary as modules found on curry.path.
Their goals narrow a flexible append: Last.last finds the last element by
solving append _ [x] == xs, Member.member solves append (xs, e : ys) =:= l,
and Nats.sub inverts add.  A goal with a parameter gets a free variable made
in Python (curry.free()); the goal and the variable go in one tuple, so each
value shows the binding beside the result.  The values of a search come in
the order of the scheduler under step mode, which the run script sets.
'''
import os, curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Last, Member, Nats

def vals(*goal):
  return list(curry.eval(*goal, converter='topython'))

def texts(*goal):
  return [str(v) for v in curry.eval(*goal)]

# Last.goal = last [1,2,3,4]: the free variable x of the rule is bound by
# the equation append _ [x] == [1,2,3,4].  One value.
print('Last.goal ->', vals(Last.goal))

# Member.goal1 x: the tuple (goal1 x, x) pairs each True with the binding of
# x.  The three members come out in the order of step mode.
x = curry.free()
print('(Member.goal1 x, x) ->', vals(([Member.goal1, x], x)))

# Member.goal2 x: membership in two lists at once; two solutions.
x = curry.free()
print('(Member.goal2 x, x) ->', vals(([Member.goal2, x], x)))

# Nats.goal1 = sub 4 2 in Peano terms: add 2 z == 4 binds z to S (S Z).
# A Peano term is a value of a user type: str shows it in Curry syntax.
print('Nats.goal1 ->', texts(Nats.goal1))

# Nats.goal2 enumerates the x with leq x 2: three values.
print('Nats.goal2 ->', texts(Nats.goal2))

# Nats.sub on Peano terms built in Python: curry.expr applies a constructor
# symbol to its arguments, and Nats.Z alone names the nullary constructor.
three = curry.expr(Nats.S, curry.expr(Nats.S, curry.expr(Nats.S, Nats.Z)))
one = curry.expr(Nats.S, Nats.Z)
print('sub 3 1 ->', texts(Nats.sub, three, one))
print('sub 1 3 ->', texts(Nats.sub, one, three))
