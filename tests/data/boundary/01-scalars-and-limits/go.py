'''
Scalar Python values cross the boundary by the conversion table.

A bool is a Bool and never an Int.  An int is a polymorphic literal, Num a
=> a, that defaults to Int as in the PAKCS REPL and fills a Float slot as a
Float.  A float is Fractional a => a.  The Int of Sprite is 64 bits on both
backends: a value past the range is refused at the boundary (#105), and an
overflow is IntOverflowError; integral division by zero is DivisionByZeroError
(#106), with no wrapped value or crash.  Each line prints a label and the value, or the
class of the error and the first line of its message.
'''
import curry

P = curry.import_('Prelude')
plus = getattr(P, '+')  # an operator is an attribute with a symbolic name

def vals(*args):
  '''The values of a goal as Python values.'''
  return list(curry.eval(*args, converter='topython'))

def show(label, thunk):
  '''Prints the value of one probe, or the class and the first line of its error.'''
  try:
    print(label, '->', repr(thunk()))
  except Exception as e:
    print(label, '!!', type(e).__name__ + ':', str(e).splitlines()[0])

# A bool is a Bool, so succ is the one of Enum Bool.  True is the last
# Bool, so succ True has no value; the bool is never the Int 1.
show('typeof True', lambda: curry.typeof(True))
show('not True', lambda: vals(getattr(P, 'not'), True))
show('succ True', lambda: vals(P.succ, True))

# The 64-bit edges.  The extreme values cross; one past them is refused
# at the boundary with the range in the message (#105, memo A3).
show('2**63 - 1', lambda: vals(2**63 - 1))
show('-2**63', lambda: vals(-2**63))
show('2**63', lambda: vals(2**63))
show('-2**63 - 1', lambda: vals(-2**63 - 1))

# Arithmetic that leaves the range, or divides by zero, is an
# IntOverflowError or DivisionByZeroError (#106). PAKCS prints
# 9223372036854775808 for the sum; "Limits" of Using the API states the
# difference.
show('2**62 + 2**62', lambda: vals(plus, 2**62, 2**62))
show('div 1 0', lambda: vals(P.div, 1, 0))
show('mod 1 0', lambda: vals(P.mod, 1, 0))

# An int is a literal: under Float it is the Float 4.0, and 1 + 2.5 is
# 3.5, as in the REPL (memo A2).
show('sqrt 4', lambda: vals(P.sqrt, 4))
show('1 + 2.5', lambda: vals(plus, 1, 2.5))
show('succ 1', lambda: vals(P.succ, 1))

# The type of a literal alone is polymorphic.  defaulted=True applies the
# table of the PAKCS REPL: Num to Int, Fractional to Float.
show('typeof 1', lambda: curry.typeof(1))
show('typeof 1, defaulted', lambda: curry.typeof(1, defaulted=True))
show('typeof 1.5', lambda: curry.typeof(1.5))
show('typeof 1.5, defaulted', lambda: curry.typeof(1.5, defaulted=True))

# succ 1.5 needs Enum a and Fractional a at once.  No entry of the table
# satisfies both, so the goal is refused with the sentence of the REPL.
show('succ 1.5', lambda: vals(P.succ, 1.5))
