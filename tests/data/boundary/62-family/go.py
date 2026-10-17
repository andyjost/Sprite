'''
The family databases of PAKCS in four styles, asked the same questions from
Python.

The four modules cross the boundary by import; the questions are the goals
of each program.  A goal with free parameters gets markers from
curry.free(), paired with the goal in a tuple to read the bindings back.
The persons are nullary constructors of a user type, so str shows the name.
family_rel asks with Boolean functions and &&, family_con with the
concurrent conjunction &, family_fun with functions and ==, family_nd with
nondeterministic functions.  The values come in the order of the scheduler
under step mode.  family_nd goal3 is not run: ancestor Andrew has no end.
'''
import os, curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import family_rel, family_con, family_fun, family_nd

def texts(*goal):
  return [str(v) for v in curry.eval(curry.expr(*goal), converter=None)]

def ask(label, goal, arity):
  '''Prints the values of goal applied to arity fresh markers.'''
  free = [curry.free() for _ in range(arity)]
  expr = ([goal] + free, *free) if arity else goal
  print('%s ->' % label, texts(expr))

for name, module in [('rel', family_rel), ('con', family_con)]:
  # goal1 child = father John child: the children of John.
  ask('%s goal1 c' % name, module.goal1, 1)
  # goal2 g c = grandfather g c: four pairs.
  ask('%s goal2 g c' % name, module.goal2, 2)

# The functional style: father is a function, so goal1 is one value.
ask('fun goal1', family_fun.goal1, 0)
# goal2 child = solve (father child == John): the children, by inversion.
ask('fun goal2 c', family_fun.goal2, 1)
ask('fun goal3 g c', family_fun.goal3, 2)
# goal4 a = ancestor a Andrew: the six ancestors of Andrew.
ask('fun goal4 a', family_fun.goal4, 1)

# The nondeterministic style: father John is one value, grandfather c is a
# nondeterministic function of c, so the pairs come as (grandparent, c).
ask('nd goal1', family_nd.goal1, 0)
ask('nd goal2 c', family_nd.goal2, 1)
