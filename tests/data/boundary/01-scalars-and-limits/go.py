'''
Scalar Python values cross the boundary by the conversion table (the
public API): a bool is a Bool, an int a polymorphic literal, a
float a concrete Float. Int values past 64 bits promote without changing
their value. A division by zero in Curry is raised from next. Each line
prints a label and the value, or the class of the error and the first line
of its message.
'''
import curry

P = curry.import_('Prelude')
plus = P['+']

def show(label, thunk):
  '''Prints the value of one probe, or the class and the first line of its error.'''
  try:
    print(label, '->', repr(thunk()))
  except Exception as e:
    print(label, '!!', type(e).__name__ + ':', str(e).splitlines()[0])

# A bool is a Bool, so succ is the one of Enum Bool.  True is the last
# Bool, so succ True has no value; the bool is never the Int 1.
show('typeof True', lambda: curry.typeof(True))
show('not True', lambda: list(curry.eval(P['not'](True))))
show('succ True', lambda: list(curry.eval(P.succ(True))))

# The 64-bit edges.  The extreme values cross; one past them is refused
# when the term is built, with the range in the message.
show('2**63 - 1', lambda: list(curry.eval(2**63 - 1)))
show('-2**63', lambda: list(curry.eval(-2**63)))
show('2**63', lambda: list(curry.eval(2**63)))
show('-2**63 - 1', lambda: list(curry.eval(-2**63 - 1)))

# Arithmetic that leaves the range, or divides by zero, is raised from
# next, with the standard class mixed in.  PAKCS has unbounded integers
# and prints 9223372036854775808 for the sum.
show('2**62 + 2**62', lambda: list(curry.eval(plus(2**62, 2**62))))
show('div 1 0', lambda: list(curry.eval(P.div(1, 0))))
show('mod 1 0', lambda: list(curry.eval(P.mod(1, 0))))

# An int is a literal: under Float it is the Float 4.0, and 1 + 2.5 is
# 3.5, as in the REPL.
show('sqrt 4', lambda: list(curry.eval(P.sqrt(4))))
show('1 + 2.5', lambda: list(curry.eval(plus(1, 2.5))))
show('succ 1', lambda: list(curry.eval(P.succ(1))))

# The type of a literal alone is polymorphic, and typeof never defaults
# (as :type).  The table of the REPL runs at eval: the Python type of the
# value shows the default.
show('typeof 1', lambda: curry.typeof(1))
show('typeof 1, defaulted', lambda: type(curry.eval(1).one()).__name__)
show('typeof 1.5', lambda: curry.typeof(1.5))
show('typeof 1.5, defaulted', lambda: type(curry.eval(1.5).one()).__name__)

# succ 1.5 needs Enum Float, which has no instance.
show('succ 1.5', lambda: list(curry.eval(P.succ(1.5))))
