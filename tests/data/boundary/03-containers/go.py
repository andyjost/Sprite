'''
Python containers cross the boundary: list, tuple, range and iterators.

A list is a Curry list with one element type.  A tuple is a Curry tuple:
() is the unit, Curry has no 1-tuple, and the Prelude stops at 15
components; both limits are checked when the term is built.  A range and any other
Sequence cross as a list.  An iterator is a lazy Curry list, consumed by
its first use, so an exhausted one is [].  Nested and shared Python data
cross as values.  Each line prints a label and the value, or the class of
the error and the first line of its message.
'''
import curry, itertools

P = curry.import_('Prelude')

def show(label, thunk):
  '''Prints the value of one probe, or the class and the first line of its error.'''
  try:
    print(label, '->', repr(thunk()))
  except Exception as e:
    print(label, '!!', type(e).__name__ + ':', str(e).splitlines()[0])

# Lists, nested and empty.
show('length [1, 2, 3]', lambda: list(curry.eval(P.length([1, 2, 3]))))
show('concat [[1, 2], [], [3]]', lambda: list(curry.eval(P.concat([[1, 2], [], [3]]))))
show('[[1, 2], [], [3]]', lambda: list(curry.eval([[1, 2], [], [3]])))

# One element type per list: 1 beside 2.5 is the Float 1.0.
show('[1, 2.5]', lambda: list(curry.eval([1, 2.5])))
show('typeof [1, 2.5]', lambda: curry.typeof([1, 2.5]))

# The tuples.  The unit crosses; the 1-tuple and the 16-tuple are refused
# when the term is built, with the limit in the message.  The 15-tuple crosses both
# ways.
show('()', lambda: list(curry.eval(())))
show('(1,)', lambda: list(curry.eval((1,))))
show('tuple(range(14))', lambda: list(curry.eval(tuple(range(14)))))
show('typeof tuple(range(15))', lambda: curry.typeof(tuple(range(15))))
show('tuple(range(15))', lambda: list(curry.eval(tuple(range(15)))))
show('tuple(range(16))', lambda: list(curry.eval(tuple(range(16)))))

# A range is a Sequence and crosses as a list, built at once.
show('range(3)', lambda: list(curry.eval(P.length(range(3)))))
show('list(range(3))', lambda: list(curry.eval(P.length(list(range(3))))))

# An iterator is a lazy list: take 3 of an infinite count ends.  The
# first use consumes it, so the second length is 0, as Python says.
show('take 3 (count 10)', lambda: list(curry.eval(P.take(3, itertools.count(10)))))
it = iter([1, 2])
show('length it', lambda: list(curry.eval(P.length(it))))
show('length it, again', lambda: list(curry.eval(P.length(it))))

# A Python list used twice crosses as a pair of equal lists.
xs = [1, 2]
show('(xs, xs)', lambda: list(curry.eval((xs, xs))))
