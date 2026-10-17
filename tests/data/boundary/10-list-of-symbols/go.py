'''
A Python list is a Curry list, and M.f(x) is the application.

A list of constructors, [M.A, M.B], is the list of two items, and a list
of functions, [M.inc, M.dbl], is a list of functions; the escapes of today
(#104), a one-element list per symbol, are now lists of lists and fail at
the type of their elements.  A tuple is a tuple.  [inc, 1] is a list whose
elements disagree in type, not the application inc 1.
'''
import curry, os

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
Items = curry.import_('Items')

def show(label, thunk):
  '''Prints the value of one probe, or the class and the first line of its error.'''
  try:
    print(label, '->', repr(thunk()))
  except Exception as e:
    print(label, '!!', type(e).__name__ + ':', str(e).splitlines()[0])

# The direct spellings run.
show('countItems [A, B]', lambda: list(curry.eval(Items.countItems([Items.A, Items.B]))))
show('applyAll [inc, dbl] 5', lambda: list(curry.eval(Items.applyAll([Items.inc, Items.dbl], 5))))

# A one-element list is a list of one element, so [[A], [B]] is a list of
# lists and fails at the type; [A] is the list of one item.
show('countItems [[A], [B]]', lambda: list(curry.eval(Items.countItems([[Items.A], [Items.B]]))))
show('countItems [A]', lambda: list(curry.eval(Items.countItems([Items.A]))))

# The same for functions: a list of lists of functions fails at the type.
show('applyAll [[inc], [dbl]] 5',
  lambda: list(curry.eval(Items.applyAll([[Items.inc], [Items.dbl]], 5))))

# A tuple is a tuple, so a pair of symbols types as a pair.
show('typeof (A, B)', lambda: curry.typeof((Items.A, Items.B)))

# [inc, 1] is a list whose elements disagree in type, refused when the
# term is built.  The application is inc(1).
show('show [inc, 1]', lambda: curry.show(curry.term([Items.inc, 1])))
show('[inc, 1]', lambda: list(curry.eval([Items.inc, 1])))
show('str inc(1)', lambda: str(Items.inc(1)))
show('inc(1)', lambda: list(curry.eval(Items.inc(1))))
