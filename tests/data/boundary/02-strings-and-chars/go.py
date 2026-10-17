'''
A Python str crosses as a Char or as a String by its length and its slot.

Python has no character type.  Under a Char slot a str of length one is a
Char; under [Char] a str of any length is a String; with no type around it
a str of length one is a Char and a longer one a String (catalogue P1).
The pick is permanent for a node built on its own, so a table built before
the call needs the typed escape.  The memo, A2, proposes that a str is
always a String and that curry.char(s) spells the character.  A Char that
leaves Curry is a Char node: it goes back in as a Char, and under the
converter it is a str of length one.
'''
import curry, os

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
P = curry.import_('Prelude')
Str = curry.import_('Str')

def vals(*args):
  '''The values of a goal as Python values.'''
  return list(curry.eval(*args, converter='topython'))

def show(label, thunk):
  '''Prints the value of one probe, or the class and the first line of its error.'''
  try:
    print(label, '->', repr(thunk()))
  except Exception as e:
    print(label, '!!', type(e).__name__ + ':', str(e).splitlines()[0])

# Alone, a str of length one is a Char and any other str is a String.
show("str(expr('a'))", lambda: str(curry.expr('a')))
show("typeof 'a'", lambda: curry.typeof('a'))
show("typeof 'ab'", lambda: curry.typeof('ab'))
show("typeof ''", lambda: curry.typeof(''))

# The slot decides: ord takes 'a' as the Char, length as the String of one
# character, and the empty str is the empty String.
show("ord 'a'", lambda: vals(P.ord, 'a'))
show("length 'a'", lambda: vals(P.length, 'a'))
show("length ''", lambda: vals(P.length, ''))
show("''", lambda: vals(''))

# show prints the Char between single quotes.  The typed escape,
# curry.typed(value, 'T'), converts the same str as a String.
show("show 'a'", lambda: vals(P.show, 'a'))
show("show (typed 'a' String)", lambda: vals(P.show, curry.typed('a', 'String')))

# A tuple typed alone keeps the Char.  The same tuple in the slot of a
# function is typed from the signature, so 'a' is a String there.
show("typeof ('a', 1)", lambda: curry.typeof(('a', 1)))
show("strInTuple ('a', 1)", lambda: vals(Str.strInTuple, ('a', 1)))
show("names [('a', 1)]", lambda: vals(Str.names, [('a', 1)]))

# A table built before the call has no slot, so its 'a' is a Char for
# good and names refuses it.  The typed escape builds it at the type.
table = curry.expr([('a', 1), ('b', 2)])
show('names table', lambda: vals(Str.names, table))
show('names (typed table)', lambda: vals(Str.names, curry.typed(table, '[(String, Int)]')))

# A Char out: the node, its type, the node back in, and the converted str.
c = next(curry.eval(P.chr, 65, converter=None))
show('chr 65', lambda: repr(c))
show('typeof (chr 65)', lambda: curry.typeof(c))
show('ord (chr 65)', lambda: vals(P.ord, c))
show('chr 65, converted', lambda: vals(P.chr, 65))
