'''
What the boundary refuses, and what it accepts in silence.

None, a dict, a set, a Python function and bytes have no row in the
conversion table and are refused when the term is built, with the spelling
that works in the message.  The Results of curry.eval are alternatives,
not a list, so they are refused as an argument.
'''
import curry, os

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
P = curry.import_('Prelude')
Rej = curry.import_('Rej')

def show(label, thunk):
  '''Prints the value of one probe, or the class and the first line of its error.'''
  try:
    print(label, '->', repr(thunk()))
  except Exception as e:
    print(label, '!!', type(e).__name__ + ':', str(e).splitlines()[0])

# No row in the table: refused when the term is built.  The message for
# None names Prelude.Nothing and P.Just(x).
show('Just None', lambda: list(curry.eval(P.Just(None))))
show("{'a': 1}", lambda: list(curry.eval({'a': 1})))
show('{1}', lambda: list(curry.eval({1})))
show('lambda x: x', lambda: list(curry.eval(lambda x: x)))

# bytes are refused and the message names decode.
show("b'ab'", lambda: list(curry.eval(b'ab')))

# The Results of curry.eval are alternatives, not the elements of a list.
show('length (eval coin)', lambda: list(curry.eval(P.length(curry.eval(Rej.coin)))))
