'''
A free variable from Python and the values of a nondeterministic goal,
under the public API.  The module Rule gives two commands for the
argument "a" and two shapes of the free list ins.  curry.eval gives the
values alone; curry.solve gives each value with the binding of the named
variable ins (the alternative's answer to issue #103).  The tuple and the
Curry function rulePair pair them too, and so does the text route.
'''
import os, curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
M = curry.import_('Rule')

# eval gives the values; solve pairs each value with the binding of ins.
# Afterwards the variable is free again and prints by its name.
ins = curry.free('ins')
print('rule "a" ins ->', list(curry.eval(M.rule('a', ins))))
print('solve rule "a" ins ->',
  [(a.value, a.bindings['ins']) for a in curry.solve(M.rule('a', ins))])
print('ins afterwards ->', [str(value) for value in curry.eval(ins)])

# A tuple that holds an anonymous variable is resolved per alternative, so
# the pairs come out as plain tuples.
ins2 = curry.free('x')
print('(rule "a" ins, ins) ->', list(curry.eval((M.rule('a', ins2), ins2))))

# The same pairing written in Curry.
print('rulePair "a" ins ->', list(curry.eval(M.rulePair('a', curry.free('x')))))

# The text route declares ins with "where ins free" and solve yields an
# Answer per value, with the value and the bindings as attributes.
goal = curry.parse('rule "a" ins where ins free', imports=[M])
for item in curry.solve(goal):
  print('text route ->', item)
  print('  value:', item.value, ' bindings:', item.bindings)
