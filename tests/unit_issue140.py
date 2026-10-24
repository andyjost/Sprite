'''
Issues #140 and #149, the C++ bindings of a node: an index at or beyond the
arity of a node raises CurryIndexError, as the former runtime does, instead
of reading past the node; a negative index counts from the end, as the Python
backend does; copy.deepcopy of a node accepts the memo argument and keeps the
sharing of one call.  The contract is the same on both backends.

The checks use raw nodes through cytest.raw.
'''
import cytest # from ./lib; must be first
import copy, curry, unittest
from curry.exceptions import CurryIndexError

class TestNodeIndex(unittest.TestCase):
  def setUp(self):
    self.P = curry.import_('Prelude')
    self.v = next(cytest.raw.values(cytest.raw.expr([1, 2])))   # a cons node: two successors

  def test_in_range(self):
    self.assertEqual(self.v[0], cytest.raw.expr(1))
    self.assertEqual(self.v[1], cytest.raw.expr([2]))

  def test_out_of_range_raises_curry_index_error(self):
    for i in (2, 5, 1000):
      with self.subTest(i=i):
        with self.assertRaises(CurryIndexError):
          self.v[i]

  def test_curry_index_error_is_an_index_error(self):
    with self.assertRaises(IndexError):
      self.v[2]

  def test_negative_index_counts_from_the_end(self):
    self.assertEqual(self.v[-1], self.v[1])
    self.assertEqual(self.v[-2], self.v[0])
    with self.assertRaises(CurryIndexError):
      self.v[-3]

  def test_nullary_node_has_no_index(self):
    nil = next(cytest.raw.values(cytest.raw.expr([])))
    with self.assertRaises(CurryIndexError):
      nil[0]

class TestDeepcopy(unittest.TestCase):
  def setUp(self):
    self.P = curry.import_('Prelude')

  def test_deepcopy_of_a_term(self):
    t = cytest.raw.expr(self.P.id, 1, typed=True)
    c = copy.deepcopy(t)
    self.assertIsNot(c, t)
    self.assertEqual(str(c), str(t))
    self.assertEqual([cytest.raw.interp().topython(v) for v in cytest.raw.values(c)], [1])

  def test_deepcopy_keeps_the_sharing_of_one_call(self):
    t = cytest.raw.expr(self.P.id, 1, typed=True)
    a, b = copy.deepcopy([t, t])
    self.assertIs(a, b)
    self.assertIsNot(a, t)

  def test_deepcopy_with_an_explicit_memo(self):
    t = cytest.raw.expr(self.P.id, 1, typed=True)
    memo = {}
    c = t.__deepcopy__(memo)
    self.assertEqual(str(c), str(t))
    self.assertIs(t.__deepcopy__(memo), c)
