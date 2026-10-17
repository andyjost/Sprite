'''
Set functions applied from Python: set0 to set2, a captured choice, the
order of Values, a failing argument, a nested set function, a free
variable in the argument.

Control.SetFunctions crosses the boundary as a module: its set0, set1 and
set2 are applied to a symbol of the module Sets and to Python values, and
sortValues, isEmpty and values2list read the set back.  The list goal
[SF.sortValues, [SF.set1, M.inc, M.coin]] is the application
sortValues (set1 inc coin).  The order of the values of a set is fixed by
sortValues; the order of the values of a search is the scheduler's under
step mode.
'''
import os, curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Sets as M
SF = curry.import_('Control.SetFunctions')

def vals(*goal):
  return list(curry.eval(*goal, converter='topython'))

def texts(*goal):
  return [str(v) for v in curry.eval(*goal, converter=None)]

# set0 over a choice: one set with both values.
print('sortValues (set0 coin) ->', vals(SF.sortValues, [SF.set0, M.coin]))
# set2 with two Python arguments: a String and a list of String.
print("sortValues (set2 rule 'a' ['x']) ->", vals(SF.sortValues, [SF.set2, M.rule, 'a', ['x']]))
print("sortValues (set2 rule 'a' ['y', 'z']) ->"
    , vals(SF.sortValues, [SF.set2, M.rule, 'a', ['y', 'z']]))
# A function that fails on its arguments: the empty set, not a failure.
print("sortValues (set2 rule 'b' ['x']) ->", vals(SF.sortValues, [SF.set2, M.rule, 'b', ['x']]))
print("isEmpty (set2 rule 'b' ['x']) ->", vals(SF.isEmpty, [SF.set2, M.rule, 'b', ['x']]))

# A nondeterministic argument is not encapsulated: one set per value of
# the argument, two values of the goal.
print('sortValues (set1 inc coin) ->', vals(SF.sortValues, [SF.set1, M.inc, M.coin]))
# A choice captured by the function value (#117): one set per value of x.
print('ord2 ->', texts(M.ord2))
# Two coins under one set0: four values, the equal ones kept.
print('twice ->', vals(M.twice))

# A failing argument under the deferred rule: the goal has no value, and
# so has isEmpty of the set.  The generator ends without a value.
print('sortValues (set1 inc failed) ->', vals(SF.sortValues, [SF.set1, M.inc, M.nothing]))
print('isEmpty (set1 inc failed) ->', vals(SF.isEmpty, [SF.set1, M.inc, M.nothing]))

# A set function inside the function of another.
print('nested ->', vals(M.nested))

# A free variable as the argument: one set per binding the rules make, and
# an empty set for each binding that matches no rule.  The count of the
# values and the sets that are not empty.
sets = [str(v) for v in curry.eval(
    SF.sortValues, [SF.set2, M.rule, 'a', curry.free()], converter=None)]
print("sortValues (set2 rule 'a' x) -> %d values, %d empty sets, and %s"
      % (len(sets), sets.count('[]'), [s for s in sets if s != '[]']))

# values2list is an IO goal: eval yields its payload.
print('values2list (set0 coin) ->', vals(SF.values2list, [SF.set0, M.coin]))
# The type of a set, and a Values value shown as text.
print('typeof (set0 coin) ->', curry.typeof(curry.expr(SF.set0, M.coin)))
print('set0 coin as text ->', texts(SF.set0, M.coin))
