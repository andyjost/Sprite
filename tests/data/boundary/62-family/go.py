'''
The family databases of PAKCS in four styles, asked the same questions from
Python (the public API).

The four modules cross the boundary by import; the questions are the goals
of each program.  A goal with free parameters is applied to named variables
from curry.free(name) and asked with curry.solve, which yields an Answer per
value, printed as the REPL prints it (a goal without parameters prints its
value alone).  The persons are nullary constructors of a user type, so
str shows the name.  family_rel asks with Boolean functions and &&,
family_con with the concurrent conjunction &, family_fun with functions and
==, family_nd with nondeterministic functions.  The values come in the order
of the scheduler under step mode.  family_nd goal3 is not run: ancestor
Andrew has no end.
'''
import os
import curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
family_rel, family_con = curry.import_('family_rel'), curry.import_('family_con')
family_fun, family_nd = curry.import_('family_fun'), curry.import_('family_nd')

def ask(label, goal):
  '''Prints the answers of goal, one text per answer.'''
  print('%s ->' % label, [str(a) for a in curry.solve(goal)])

for name, module in [('rel', family_rel), ('con', family_con)]:
  c, g = curry.free('c'), curry.free('g')
  # goal1 child = father John child: the children of John.
  ask('%s goal1 c' % name, module.goal1(c))
  # goal2 g c = grandfather g c: four pairs.
  ask('%s goal2 g c' % name, module.goal2(g, c))

# The functional style: father is a function, so goal1 is one value.
c, g, a = curry.free('c'), curry.free('g'), curry.free('a')
ask('fun goal1', family_fun.goal1)
# goal2 child = solve (father child == John): the children, by inversion.
ask('fun goal2 c', family_fun.goal2(c))
ask('fun goal3 g c', family_fun.goal3(g, c))
# goal4 a = ancestor a Andrew: the six ancestors of Andrew.
ask('fun goal4 a', family_fun.goal4(a))

# The nondeterministic style: father John is one value, grandfather c is a
# nondeterministic function of c, so the answers pair c with the grandparent.
c = curry.free('c')
ask('nd goal1', family_nd.goal1)
ask('nd goal2 c', family_nd.goal2(c))
