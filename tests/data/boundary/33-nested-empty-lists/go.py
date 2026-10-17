'''
A value that holds the empty list at two types crosses back into a typed
call (issue #108), on the public API.  A value of a built-in type
is Python data, so a list value crosses back as a fresh term typed at the
call; a term object placed twice is one node; a str is a String;
curry.term(x, type=) states a type.
'''
import curry

P = curry.import_('Prelude')

def show(label, thunk):
  try:
    print(label, '->', repr(thunk()))
  except Exception as error:
    print(label, '!!', type(error).__name__ + ':', str(error).splitlines()[0])

# The lines of the issue: a value with [] at the end of two lists, of two
# strings, of a list beside a string, typed and passed back in.
v = curry.eval([[1, 2], [3]]).one()
show('typeof [[1, 2], [3]]', lambda: curry.typeof(v))
strs = curry.eval(['ab', 'c']).one()
show("typeof ['ab', 'c']", lambda: curry.typeof(strs))
show('unwords strs', lambda: curry.eval(P.unwords(strs)).one())
pair = curry.eval(([1], 'ab')).one()
show("typeof ([1], 'ab')", lambda: curry.typeof(pair))
one_nil = curry.eval([[1]]).one()
show('typeof [[1]]', lambda: curry.typeof(one_nil))

# No raw route: [] beside a list of Ints is a term.  A term object reused
# at two types in one term is one node.
show('typeof term [[1, 2], []]', lambda: curry.typeof(curry.term([[1, 2], []])))
e = curry.term([])
show('typeof (e, length e)', lambda: curry.typeof((e, P.length(e))))
show("typeof [e, 'ab']", lambda: curry.typeof([e, 'ab']))

# One [] value at two types in one call.
nil = curry.eval([]).one()
show('typeof nil', lambda: curry.typeof(nil))
show('id ([[1], nil], [["a"], nil])', lambda: curry.eval(P.id(([[1], nil], [['a'], nil]))).one())
show("id (nil :: [Int], nil :: String)",
  lambda: curry.eval(P.id((
      curry.term(nil, type='[Int]'), curry.term(nil, type='String')))).one())

# A value with [] at two types, typed on the way in, typed on the way out.
two = curry.eval(curry.term(([], ''), type='([Int], String)')).one()
show('typeof two', lambda: curry.typeof(two))
show('id two', lambda: curry.eval(P.id(two)).one())
show('id (two, strs)', lambda: curry.eval(P.id((two, strs))).one())
