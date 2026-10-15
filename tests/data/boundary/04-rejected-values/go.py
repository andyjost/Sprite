'''
What the boundary refuses, and what it accepts in silence.

None, a dict, a set and a Python function have no row in the conversion
table and are refused at the call.  A bytes value crosses as a String,
which the memo, A2, proposes to refuse.  The generator of curry.eval is an
iterator, so the values of one goal become a lazy list in the next goal
without a word (catalogue P9).  The marker curry.unboxed outside a
primitive was a crash on the C++ backend and is a ConversionError at
construction since #107.  The converter of curry.eval: an unknown name is
silent, a positional name joins the arguments of the goal (P13), and the
callable protocol is f(interp, value), so str alone fails (P14).
'''
import curry, os

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
P = curry.import_('Prelude')
Rej = curry.import_('Rej')

def vals(*args):
  '''The values of a goal as Python values.'''
  return list(curry.eval(*args, converter='topython'))

def show(label, thunk):
  '''Prints the value of one probe, or the class and the first line of its error.'''
  try:
    print(label, '->', repr(thunk()))
  except Exception as e:
    print(label, '!!', type(e).__name__ + ':', str(e).splitlines()[0])

def error_class(thunk):
  '''The class of the error of a probe alone, for a message that names the backend.'''
  try:
    return thunk()
  except Exception as e:
    return type(e).__name__

# No row in the table: refused at the call.  The message for None names
# the slot and its type, not Prelude.Nothing.
show('Just None', lambda: vals(P.Just, None))
show("{'a': 1}", lambda: vals({'a': 1}))
show('{1}', lambda: vals({1}))
show('lambda x: x', lambda: vals(lambda x: x))

# A wart: bytes cross as a String.  A2 refuses them and names b.decode().
show("b'ab'", lambda: vals(b'ab'))

# The generator of curry.eval is an iterator, so the two values of coin
# are the two elements of a lazy list (P9).
show('length (eval coin)', lambda: vals(P.length, curry.eval(Rej.coin)))

# The marker of a payload outside a primitive: an error at construction
# that names the spelling, where #107 was a crash of the process.
show('id (unboxed 1)', lambda: vals(P.id, curry.unboxed(1)))

# The converter.  'bogus' is silent and leaves the Curry node (P13).  A
# positional 'topython' is an argument of inc, so the error names inc.
show("converter='bogus'", lambda: list(curry.eval(Rej.inc, 1, converter='bogus')))
show("'topython' positional", lambda: list(curry.eval(Rej.inc, 1, 'topython')))
show('converter=None', lambda: list(curry.eval(Rej.inc, 1, converter=None)))

# A callable converter takes the interpreter and the value (P14).  str
# alone gets the interpreter as its value and fails; its message names the
# node class of the backend, so the line prints the class of the error.
convert = lambda interp, value: ('converted', str(value))
show('converter=convert', lambda: list(curry.eval(Rej.inc, 1, converter=convert)))
show('converter=str', lambda: error_class(lambda: list(curry.eval(Rej.inc, 1, converter=str))))
