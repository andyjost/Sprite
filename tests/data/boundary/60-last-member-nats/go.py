'''
Narrowing by inversion, driven from Python.

The port of 60-last-member-nats to the public API.  Three programs
of PAKCS cross the boundary as modules found on curry.path.  Their goals
narrow a flexible append: Last.last finds the last element by solving
append _ [x] == xs, Member.member solves append (xs, e : ys) =:= l, and
Nats.sub inverts add.  A goal with a parameter gets a named free variable
made in Python (curry.free('x')); curry.solve then yields an Answer, the
value with the binding of x beside it, without a tuple.  A Peano term is
built by calling the constructors; a value of a user type comes back as a
Data, whose repr is the Curry text.  The values of a search come in the
order of the scheduler under step mode.
'''
import os, curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Last, Member, Nats

# Last.goal = last [1,2,3,4]: the free variable x of the rule is bound by
# the equation append _ [x] == [1,2,3,4].  One value.
print('Last.goal ->', list(curry.eval(Last.goal)))

# Member.goal1 x: each answer is True with the binding of x.  The three
# members come out in the order of step mode.
x = curry.free('x')
print('Member.goal1 x ->', list(curry.solve(Member.goal1(x))))

# Member.goal2 x: membership in two lists at once; two solutions.
x = curry.free('x')
print('Member.goal2 x ->', list(curry.solve(Member.goal2(x))))

# Nats.goal1 = sub 4 2 in Peano terms: add 2 z == 4 binds z to S (S Z).
# A Peano term is a value of a user type: a Data, shown in Curry syntax.
print('Nats.goal1 ->', list(curry.eval(Nats.goal1)))

# Nats.goal2 enumerates the x with leq x 2: three values.
print('Nats.goal2 ->', list(curry.eval(Nats.goal2)))

# Nats.sub on Peano terms built in Python: a constructor is called with its
# arguments, and Nats.Z alone is the term of the nullary constructor.
three = Nats.S(Nats.S(Nats.S(Nats.Z)))
one = Nats.S(Nats.Z)
print('sub 3 1 ->', list(curry.eval(Nats.sub(three, one))))
print('sub 1 3 ->', list(curry.eval(Nats.sub(one, three))))
