'''
Sharing at the boundary under the public API: a term object used
twice, a module attribute used twice, a cycle spelled in Curry text.

Curry evaluates by call-time choice: one node has one value wherever it is
shared.  A term object, t = Coin.coin, is one node, so (t, t) has two
values.  The attribute Coin.coin read twice builds two nodes, so
(Coin.coin, Coin.coin) has four, as coin + coin has in Curry, and
double coin has two because double shares its parameter.  A cycle is
Curry text through curry.parse.  curry.choice takes two operands or more.
'''
import curry, os

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
P = curry.import_('Prelude')
Coin = curry.import_('Coin')

def show(label, thunk):
  '''Prints the value of one probe, or the class and the first line of its error.'''
  try:
    print(label, '->', repr(thunk()))
  except Exception as e:
    print(label, '!!', type(e).__name__ + ':', str(e).splitlines()[0])

# The coin lines.  One node used twice against the attribute read twice.
t = Coin.coin
show('(t, t)', lambda: list(curry.eval((t, t))))
show('(coin, coin)', lambda: list(curry.eval((Coin.coin, Coin.coin))))
show('double coin', lambda: list(curry.eval(Coin.double(Coin.coin))))
show('coin + coin', lambda: list(curry.eval(Coin.coin + Coin.coin)))

# An evaluated term keeps its values.
show('vals(t)', lambda: list(curry.eval(t)))
show('vals(t), again', lambda: list(curry.eval(t)))

# A cycle in Curry text: a = 1 : a, and take 3 of it.
ones = curry.parse('let a = 1 : a in a')
show('str (take 3 a)', lambda: str(P.take(3, ones)))
show('take 3 a', lambda: list(curry.eval(P.take(3, ones))))

# One choice term placed twice is one node: two values.
# Two choice terms are two nodes: four values.
c = curry.choice(1, 2)
show('(c, c)', lambda: list(curry.eval((c, c))))
show('(1 ? 2, 1 ? 2)', lambda: list(curry.eval((curry.choice(1, 2), curry.choice(1, 2)))))

# curry.choice(a, b, *more): three operands are a three-way choice.
show('str (choice 1 2)', lambda: str(curry.choice(1, 2)))
show('choice 1 2', lambda: list(curry.eval(curry.choice(1, 2))))
show('choice 1 2 3', lambda: list(curry.eval(curry.choice(1, 2, 3))))
