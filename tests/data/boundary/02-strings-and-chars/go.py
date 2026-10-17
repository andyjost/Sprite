'''
A Python str is always a String; curry.Char is the character.

Python has no character type.  Under the public API a str of
any length is a String, the empty string and one character included, so a
Char slot refuses a str and names curry.Char.  A Char that leaves Curry
comes back as a curry.Char, a str of length one that goes back into a Char
slot as it is.
'''
import curry, os

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
P = curry.import_('Prelude')
Str = curry.import_('Str')

def show(label, thunk):
  '''Prints the value of one probe, or the class and the first line of its error.'''
  try:
    print(label, '->', repr(thunk()))
  except Exception as e:
    print(label, '!!', type(e).__name__ + ':', str(e).splitlines()[0])

# Alone, a str of any length is a String.
show("show('a')", lambda: curry.show('a'))
show("typeof 'a'", lambda: curry.typeof('a'))
show("typeof 'ab'", lambda: curry.typeof('ab'))
show("typeof ''", lambda: curry.typeof(''))

# The type decides nothing: ord refuses the str and names curry.Char;
# length takes 'a' as the String of one character.  A bare str is not a
# goal; curry.term spells the String as one.
show("ord 'a'", lambda: list(curry.eval(P.ord('a'))))
show("ord (Char 'a')", lambda: list(curry.eval(P.ord(curry.Char('a')))))
show("length 'a'", lambda: list(curry.eval(P.length('a'))))
show("length ''", lambda: list(curry.eval(P.length(''))))
show("'' as a goal", lambda: list(curry.eval('')))
show("term ''", lambda: list(curry.eval(curry.term(''))))

# show prints the Char between single quotes and the String between
# double quotes.
show("show (Char 'a')", lambda: list(curry.eval(P.show(curry.Char('a')))))
show("show 'a'", lambda: list(curry.eval(P.show('a'))))

# A tuple typed alone holds a String, as it does in the slot of a
# function.
show("typeof ('a', 1)", lambda: curry.typeof(('a', 1)))
show("strInTuple ('a', 1)", lambda: list(curry.eval(Str.strInTuple(('a', 1)))))
show("names [('a', 1)]", lambda: list(curry.eval(Str.names([('a', 1)]))))

# A table built before the call is a Python list; it is typed with the
# call, so no typed escape is needed.
table = [('a', 1), ('b', 2)]
show('names table', lambda: list(curry.eval(Str.names(table))))

# A Char out: a curry.Char, which types as a Char and goes back into ord
# as it is.
c = next(curry.eval(P.chr(65)))
show('chr 65', lambda: repr(c))
show('typeof (chr 65)', lambda: curry.typeof(c))
show('ord (chr 65)', lambda: list(curry.eval(P.ord(c))))
show('chr 65 == "A"', lambda: c == 'A')
