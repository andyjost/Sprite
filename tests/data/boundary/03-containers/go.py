'''
Python containers cross the boundary: list, tuple, range and iterators.

A list is a Curry list with one element type.  A tuple is a Curry tuple:
() is the unit, Curry has no 1-tuple, and the Prelude stops at 15
components (catalogue P8).  A range does not cross.  An iterator is a lazy
Curry list, consumed by its first use, so an exhausted one is [] (P9).
Nested and shared Python data cross as values.  Each line prints a label
and the value, or the class of the error and the first line of its message.
'''
import curry, itertools

P = curry.import_('Prelude')

def vals(*args):
  '''The values of a goal as Python values.'''
  return list(curry.eval(*args, converter='topython'))

def show(label, thunk):
  '''Prints the value of one probe, or the class and the first line of its error.'''
  try:
    print(label, '->', repr(thunk()))
  except Exception as e:
    print(label, '!!', type(e).__name__ + ':', str(e).splitlines()[0])

# Lists, nested and empty.
show('length [1, 2, 3]', lambda: vals(P.length, [1, 2, 3]))
show('concat [[1, 2], [], [3]]', lambda: vals(P.concat, [[1, 2], [], [3]]))
show('[[1, 2], [], [3]]', lambda: vals([[1, 2], [], [3]]))

# One element type per list: 1 beside 2.5 is the Float 1.0 (memo A2).
show('[1, 2.5]', lambda: vals([1, 2.5]))
show('typeof [1, 2.5]', lambda: curry.typeof([1, 2.5]))

# The tuples.  The unit crosses, the 1-tuple is refused at the expression,
# and the 16-tuple fails after the typing with an error that names a
# symbol the user never wrote (P8).  The 15-tuple crosses in, but the
# converter stops at 14 components and hands the node back for 15.
show('()', lambda: vals(()))
show('(1,)', lambda: vals((1,)))
show('tuple(range(14))', lambda: vals(tuple(range(14))))
show('typeof tuple(range(15))',
     lambda: curry.typeof(next(curry.eval(tuple(range(15)), converter=None))))
show('tuple(range(15))', lambda: vals(tuple(range(15))))
show('tuple(range(16))', lambda: vals(tuple(range(16))))

# A range has no row in the table; list(range(3)) is the spelling.
show('range(3)', lambda: vals(P.length, range(3)))
show('list(range(3))', lambda: vals(P.length, list(range(3))))

# An iterator is a lazy list: take 3 of an infinite count ends.  The
# first use consumes it, so the second length is 0 (P9).
show('take 3 (count 10)', lambda: vals(P.take, 3, itertools.count(10)))
it = iter([1, 2])
show('length it', lambda: vals(P.length, it))
show('length it, again', lambda: vals(P.length, it))

# A Python list used twice crosses as a pair of equal lists.
xs = [1, 2]
show('(xs, xs)', lambda: vals((xs, xs)))
