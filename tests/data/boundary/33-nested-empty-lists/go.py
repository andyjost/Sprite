'''
A value that holds the empty list at two types crosses back into a typed
call (issue #108, open).  The issue reports that the typed walk, which
memoizes by node, types the shared empty list once and fails the second
occurrence at another type on the C++ backend.  At the revision of this
driver every line passes on both backends, and the driver pins that: a
regression shows as a MismatchError in the output.
'''
import curry

P = curry.import_('Prelude')

def vals(*goal, **kwds):
  return list(curry.eval(*goal, converter='topython', **kwds))

def show(label, thunk):
  try:
    print(label, '->', repr(thunk()))
  except BaseException as error:  # EvaluationError is not an Exception (P42)
    print(label, '!!', type(error).__name__ + ':', str(error).splitlines()[0])

# The lines of the issue: a value of eval with [] at the end of two lists,
# of two strings, of a list beside a string, typed and passed back in.
v, = curry.eval([[1, 2], [3]])
show('typeof [[1, 2], [3]]', lambda: curry.typeof(v))
strs, = curry.eval(['ab', 'c'])
show("typeof ['ab', 'c']", lambda: curry.typeof(strs))
show('unwords strs', lambda: vals(P.unwords, strs))
pair, = curry.eval(([1], 'ab'))
show("typeof ([1], 'ab')", lambda: curry.typeof(pair))
one_nil, = curry.eval([[1]])
show('typeof [[1]]', lambda: curry.typeof(one_nil))

# A raw node with [] beside a list of Ints, and a recorded curry.expr([])
# reused at two types in one expression.
show('typeof raw_expr [[1, 2], []]', lambda: curry.typeof(curry.raw_expr([[1, 2], []])))
e = curry.expr([])
show('typeof (e, length e)', lambda: curry.typeof(curry.expr((e, [P.length, e]))))
show("typeof [e, 'ab']", lambda: curry.typeof(curry.expr([e, 'ab'])))

# One [] node of a value at two types in one call.  On the C++ backend the
# empty list is one shared node (curry.expr([]) is curry.expr([]) holds
# there and not on the Python backend; see the README), so this is the
# case the issue names.
nil, = curry.eval([])
show('typeof nil', lambda: curry.typeof(nil))
show('id ([[1], nil], [["a"], nil])', lambda: vals(P.id, ([[1], nil], [['a'], nil])))
show("id (nil :: [Int], nil :: String)",
     lambda: vals(P.id, (curry.typed(nil, '[Int]'), curry.typed(nil, 'String'))))

# A value with [] at two types, typed on the way in, typed on the way out.
two, = curry.eval(curry.typed(([], ''), '([Int], String)'))
show('typeof two', lambda: curry.typeof(two))
show('id two', lambda: vals(P.id, two))
show('id (two, strs)', lambda: vals(P.id, (two, strs)))
