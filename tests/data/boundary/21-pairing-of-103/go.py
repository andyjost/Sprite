'''
A free variable from Python and the values of a nondeterministic goal.  The
module Rule gives two commands for the argument "a" and two shapes of the
free list ins.  Which binding of ins goes with which command is observable
only through a value that holds the variable: a tuple built in Python, a
Curry function that returns the pair, or the text route.  The marker itself
never receives a binding (issue #103, open).
'''
import os, curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
M = curry.import_('Rule')

def vals(*goal, **kwds):
  return list(curry.eval(curry.expr(*goal, **kwds), converter='topython'))

def texts(*goal, **kwds):
  kwds.setdefault('converter', None)
  return [str(value) for value in curry.eval(*goal, **kwds)]

# The pairing is lost: the values come without their binding, and the marker
# afterwards is a free variable (P24).  A fixed system (#103, memo A11) pairs
# each value with its binding of ins.
ins = curry.free()
print('rule "a" ins ->', vals(M.rule, 'a', ins))
print('ins afterwards ->', texts(ins))

# The escape: a tuple that holds the variable is resolved per alternative,
# so the pairs come out.
ins2 = curry.free()
print('(rule "a" ins, ins) ->', vals(([M.rule, 'a', ins2], ins2)))

# The same pairing written in Curry.
print('rulePair "a" ins ->', vals(M.rulePair, 'a', curry.free()))

# A positional after a list goal is an error today, not a request for the
# binding (P24).  The message holds a repr with an address, so the class
# alone is printed.
ins4 = curry.free()
try:
  curry.eval([M.rule, 'a', ins4], ins4, converter=None)
except curry.CurryTypeError as error:
  print('eval([rule, "a", ins], ins) !!', type(error).__name__)

# The text route lifts "where ins free" and yields a Bindings per value,
# with the value and the bindings as attributes (P20).
goal = curry.compile('rule "a" ins where ins free', mode='expr', imports=[M])
for item in curry.eval(goal, converter=None):
  print('text route ->', item)
  print('  value:', item.value, ' bindings:', item.bindings)
