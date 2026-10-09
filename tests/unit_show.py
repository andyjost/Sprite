'''
show of a shared node and of a cycle, on both backends (issue #119).

The printer writes an ellipsis for a node that closes a cycle: a node met
again while it is on the path from the root to the current node.  A node met
again elsewhere is shared, not cyclic, and is written in full every time.

The C++ printer (graph/show.cpp) took the second occurrence of a shared node
for a cycle.  It kept every node met in a multiset, and when the walk left a
node it removed the cursor of the walk, which is the last successor visited
and not the node left, so a node stayed in the multiset after the walk left
it: goal of data/curry/SharedListPrinter.curry printed ([False], ...) where
the Python backend and PAKCS print ([False], [False]).  The printer keeps the
path now.  The Python printer (show.py) kept the count of a spine node that
closed a cycle, so a cyclic list shared by two positions printed as ... at
the second: ([1, ...], ...) for let a = 1:a in (a, a).  Both backends print
every occurrence of a shared node in full now, and a cycle as before.
'''
import cytest # from ./lib; must be first
from curry.expressions import ref
import curry, unittest

class TestSharedValues(cytest.TestCase):
  '''The goals of the issue, evaluated.'''
  @classmethod
  def setUpClass(cls):
    cls.M = curry.import_('SharedListPrinter')

  def test_shared_list(self):
    values = [str(value) for value in curry.eval(self.M.goal)]
    self.assertEqual(values, ['([False], [False])'])

  def test_shared_choice(self):
    values = sorted(str(value) for value in curry.eval(self.M.goal2))
    self.assertEqual(values, ['([False], [False], 1)', '([], [], 1)'])


class TestSharedExpressions(cytest.TestCase):
  '''A shared acyclic node is written in full at every occurrence.'''
  def check(self, expr, text, repr_text=None):
    self.assertEqual(str(expr), text)
    if repr_text is not None:
      self.assertEqual(repr(expr), repr_text)

  def test_shared_list_in_tuple(self):
    # let d = [False] in (d, d)
    e = curry.raw_expr((ref('d'), ref('d')), d=[False])
    self.assertIs(e[0], e[1])
    self.check(e, '([False], [False])', '<(,) <: <False> <[]>> <: <False> <[]>>>')

  def test_shared_constructor(self):
    prelude = curry.import_('Prelude')
    # let d = Just 1 in (d, d) and in [d, d]
    e = curry.raw_expr((ref('d'), ref('d')), d=[prelude.Just, 1])
    self.check(e, '(Just 1, Just 1)', '<(,) <Just <Int 1>> <Just <Int 1>>>')
    e = curry.raw_expr([ref('d'), ref('d')], d=[prelude.Just, 1])
    self.check(e, '[Just 1, Just 1]')

  def test_shared_string(self):
    # let d = "ab" in (d, d)
    e = curry.raw_expr((ref('d'), ref('d')), d='ab')
    self.check(e, '("ab", "ab")')

  def test_shared_list_in_list(self):
    # let d = [1, 2] in [d, d]
    e = curry.raw_expr([ref('d'), ref('d')], d=[1, 2])
    self.check(e, '[[1, 2], [1, 2]]')

  def test_shared_open_list(self):
    # let d = 1 : x in (d, d) with x free
    e = curry.raw_expr((ref('d'), ref('d')), d=curry.cons(1, curry.free(7)))
    self.check(e, '(1:_a, 1:_a)')

  def test_shared_head_and_tail(self):
    # let d = [1] in d : d, the list [[1], 1]
    e = curry.raw_expr(curry.cons(ref('d'), ref('d')), d=[1])
    self.assertIs(e[0], e[1])
    self.check(e, '[[1], 1]')


class TestCyclicExpressions(cytest.TestCase):
  '''
  A cycle prints as before: an ellipsis where the walk meets a node of the
  path again.  The texts were observed on both backends before the change.
  '''
  def check(self, expr, text, repr_text=None):
    self.assertEqual(str(expr), text)
    if repr_text is not None:
      self.assertEqual(repr(expr), repr_text)

  def cyclic_list(self):
    # let a = 1 : a in a
    e = curry.raw_expr(ref('a'), a=curry.cons(1, ref('a')))
    self.assertIs(e[1], e)
    return e

  def test_cyclic_list(self):
    self.check(self.cyclic_list(), '[1, ...]', '<: <Int 1> ...>')

  def test_cycle_of_two_nodes(self):
    # let a = 1 : b, b = 2 : a in a
    e = curry.raw_expr(ref('a'), a=curry.cons(1, ref('b')), b=curry.cons(2, ref('a')))
    self.check(e, '[1, 2, ...]', '<: <Int 1> <: <Int 2> ...>>')

  def test_cycle_through_constructor(self):
    prelude = curry.import_('Prelude')
    # let a = Just a in a
    e = curry.raw_expr(ref('a'), a=[prelude.Just, ref('a')])
    self.check(e, 'Just ...', '<Just ...>')

  def test_cycle_through_tuple(self):
    # let a = (a, 1) in a
    e = curry.raw_expr(ref('a'), a=(ref('a'), 1))
    self.check(e, '(..., 1)', '<(,) ... <Int 1>>')

  def test_cyclic_string(self):
    '''
    A cyclic list of Chars is no string: the string style met the cycle and
    did not end on the Python backend.  The list style writes it.
    '''
    # let s = 'a' : s in s
    s = curry.raw_expr(ref('s'), s=curry.cons('a', ref('s')))
    self.assertIs(s[1], s)
    self.check(s, "['a', ...]", "<: <Char 'a'> ...>")
    self.check(curry.raw_expr((s, s)), "(['a', ...], ['a', ...])")
    # A string whose tail is a cycle of two nodes.
    e = curry.raw_expr(ref('a'), a=curry.cons('a', ref('b')), b=curry.cons('b', ref('a')))
    self.check(e, "['a', 'b', ...]")

  def test_shared_cyclic_list(self):
    '''
    A cyclic list at two positions: each occurrence is written in full, with
    its own ellipsis.  Before the change the second occurrence was an
    ellipsis on both backends.
    '''
    a = self.cyclic_list()
    self.check(curry.raw_expr((a, a)), '([1, ...], [1, ...])')
    self.check(curry.raw_expr([a, a]), '[[1, ...], [1, ...]]')
    # a : a is the list whose head is a and whose spine continues into a.
    self.check(curry.raw_expr(curry.cons(a, a)), '[[1, ...], 1, ...]')


if __name__ == '__main__':
  unittest.main()
