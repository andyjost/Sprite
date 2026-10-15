'''
Sharing at the boundary: a term object used twice, a symbol used twice,
anchors and curry.ref for shared and cyclic subterms.

Curry evaluates by call-time choice: one node has one value wherever it is
shared.  A Python object that holds an expression, t = curry.expr(M.coin),
is one node, so (t, t) has two values.  The symbol M.coin written twice
builds two nodes, so (M.coin, M.coin) has four, as coin + coin has in
Curry, and double coin has two because double shares its parameter.  An
anchor, a keyword of curry.expr, names a subterm that curry.ref refers to,
for a shared choice or a cycle; the trap is that a misspelt option is an
anchor as well (catalogue P5).  curry.choice takes an id first, so three
arguments are a two-way choice (P6).  The repr of an evaluated term is not
printed: the C++ backend leaves a forward node where the Python backend
shows the value (P17); its values are the same on a second evaluation.
'''
import curry, os

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
P = curry.import_('Prelude')
Coin = curry.import_('Coin')

def vals(*args, **anchors):
  '''The values of a goal as Python values, in the order of step mode.'''
  return list(curry.eval(*args, converter='topython', **anchors))

def show(label, thunk):
  '''Prints the value of one probe, or the class and the first line of its error.'''
  try:
    print(label, '->', repr(thunk()))
  except Exception as e:
    print(label, '!!', type(e).__name__ + ':', str(e).splitlines()[0])

# The coin lines.  One node used twice against the symbol used twice.
t = curry.expr(Coin.coin)
show('(t, t)', lambda: vals((t, t)))
show('(coin, coin)', lambda: vals((Coin.coin, Coin.coin)))
show('double coin', lambda: vals(Coin.double, Coin.coin))
show('coin + coin', lambda: vals(getattr(P, '+'), Coin.coin, Coin.coin))

# An evaluated term keeps its values: the typed walk records its type.
show('vals(t)', lambda: vals(t))
show('vals(t), again', lambda: vals(t))

# A cycle through an anchor: a = 1 : a, and take 3 of it.
ones = lambda: curry.cons(1, curry.ref('a'))
show('str (take 3 a)', lambda: str(curry.expr(P.take, 3, curry.ref('a'), a=ones())))
show('take 3 a', lambda: vals(P.take, 3, curry.ref('a'), a=ones()))

# One anchor over a choice, referenced twice, is one node: two values.
# Two choice markers are two nodes: four values.
show('(c, c)', lambda: vals((curry.ref('c'), curry.ref('c')), c=curry.choice(1, 2)))
show('(1 ? 2, 1 ? 2)', lambda: vals((curry.choice(1, 2), curry.choice(1, 2))))

# The anchor trap: convertor is not converter, so it is an unused anchor
# and the goal yields the Curry node (P5).
show("convertor='topython'", lambda: list(curry.eval(Coin.inc, 1, convertor='topython')))

# curry.choice(cid, lhs, rhs): with three arguments the first is the id.
show('str (choice 1 2)', lambda: str(curry.expr(curry.choice(1, 2))))
show('choice 1 2', lambda: vals(curry.choice(1, 2)))
show('choice 1 2 3', lambda: vals(curry.choice(1, 2, 3)))
