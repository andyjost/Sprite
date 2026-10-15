'''
A Python list whose first element is a symbol is an application (#104).

The rule exists to spell a nested application, [M.f, x], and it is read by
the first element alone.  So a list of constructors, [M.A, M.B], is the
application A B, which fails on the arity of A, and a list of functions,
[M.inc, M.dbl], is inc dbl, which fails on a type mismatch (catalogue P2).
The errors name the symptom and not the rule (P44).  The escapes are a
one-element list per symbol, [[M.A], [M.B]], or curry.expr(M.A) for the
first element.  A tuple is never an application.  This driver pins today's
output: a fixed system (memo A1, where a list is a list and M.f(x) is the
application) prints 2 and [6, 10] for the direct spellings.
'''
import curry, os

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
Items = curry.import_('Items')

def vals(*args):
  '''The values of a goal as Python values.'''
  return list(curry.eval(*args, converter='topython'))

def show(label, thunk):
  '''Prints the value of one probe, or the class and the first line of its error.'''
  try:
    print(label, '->', repr(thunk()))
  except Exception as e:
    print(label, '!!', type(e).__name__ + ':', str(e).splitlines()[0])

# The direct spellings fail today (#104).  The first is the arity of A;
# the second is the type of the argument of inc.
show('countItems [A, B]', lambda: vals(Items.countItems, [Items.A, Items.B]))
show('applyAll [inc, dbl] 5', lambda: vals(Items.applyAll, [Items.inc, Items.dbl], 5))

# A one-element list of a nullary symbol is its value, so [A] is A and
# [[A], [B]] is the list of two items.  [A] alone is not a list of Item.
show('countItems [[A], [B]]', lambda: vals(Items.countItems, [[Items.A], [Items.B]]))
show('countItems [A]', lambda: vals(Items.countItems, [Items.A]))

# An expression as the first element makes the list a list.
show('countItems [expr A, B]', lambda: vals(Items.countItems, [curry.expr(Items.A), Items.B]))

# The same escape for functions: a partial application of zero arguments.
show('applyAll [[inc], [dbl]] 5', lambda: vals(Items.applyAll, [[Items.inc], [Items.dbl]], 5))

# A tuple is never an application, so a pair of symbols types as a pair.
show('typeof (A, B)', lambda: curry.typeof((Items.A, Items.B)))

# The rule at work: [inc, 1] is the application inc 1.
show('str [inc, 1]', lambda: str(curry.expr([Items.inc, 1])))
show('[inc, 1]', lambda: vals([Items.inc, 1]))
