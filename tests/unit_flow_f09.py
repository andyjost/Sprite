'''
F09: acceptance of the recommended Python API.

Trace: alt.py and alt.{cxx,py}.out.2; line numbers include the
recorded command header when present. Each row names its flip lane.
  test_point_value: alt.py 9-13; output 1-4; lane 6.
  test_data_has_no_sequence_protocol: alt.py 14-15; output 5-6; lane 2.
  test_pass_data_back: alt.py 16; output 7; lane 2.
  test_tree_values: alt.py 17-20; output 8-10; lane 6.
  test_function_value: alt.py 21-24; output 11-13; lane 3.
  test_char_and_string_values: alt.py 25-29; output 14-17; lane 2.
  test_print_type_and_hash_values: alt.py 30-33; output 18-21; lane 2.
  test_constructor_classes: alt.py A26; tree_example.py 38-49, 59-67; output decision (f); lane 6.
  test_nested_patterns: alt.py A26; tree_example.py 51-66; output decision (f); lane 6.

Left out: No semantic lines omitted. Harness show is replaced by unittest.

Departures and rules: Decision (a), Appendix A 6081-6088: sorted Tree values must raise
TypeError. Decision (f), A26 and section 12: Point is the constructor class, not the
generic Data name in output 1; Tree patterns use curry.info(T).types and
T.Node.datatype. tree_example.py 38-67 supplies the pattern values.

Lanes refer to the Python API implementation plan. Tests import curry,
the package. Missing proposed names are only used inside test methods.
'''
import cytest # from ./lib; must be first
import curry
import unittest
import os

FLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'curry', 'flows')


def setUpModule():
  curry.path.insert(0, FLOW_PATH)


class TestFlowF09(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  def test_point_value(self):
    G = curry.import_('Geo'); p = curry.eval(G.origin).one(); q = curry.eval(G.Point(0, 0)).one()
    self.assertIsInstance(p, curry.Data)
    self.assertIs(type(p), G.Point)
    self.assertEqual(str(p), 'Point 0 0')
    self.assertEqual(p, q)
    self.assertEqual(p, G.Point(0, 0))
    self.assertNotEqual(p, (0, 0))
    self.assertEqual(hash(p), hash(q))
    self.assertEqual(len({p, q}), 1)
    self.assertTrue(p)
    self.assertEqual((p.symbol.name, p.args, p.args[1]), ('Point', (0, 0), 0))

  def test_data_has_no_sequence_protocol(self):
    G = curry.import_('Geo'); p = curry.eval(G.origin).one()
    with self.assertRaises(TypeError):
      p[0]
    with self.assertRaises(TypeError):
      len(p)

  def test_pass_data_back(self):
    G = curry.import_('Geo'); p = curry.eval(G.origin).one()
    self.assertEqual((curry.eval(G.norm1(p)).one(), curry.eval(G.norm1(G.Point(3, -4))).one()), (0, 7))

  def test_tree_values(self):
    G = curry.import_('Geo'); t = curry.eval(G.Node(G.Leaf, -1, G.Leaf)).one(); leaf = curry.eval(G.Leaf).one()
    self.assertEqual((str(t), t.args[1], str(leaf)), ('Node Leaf (-1) Leaf', -1, 'Leaf'))
    with self.assertRaises(TypeError):
      sorted([t, leaf])
    self.assertEqual(leaf, G.Leaf)
    self.assertEqual(leaf, curry.eval(G.Leaf).one())
    self.assertEqual(t, t)

  def test_function_value(self):
    P = curry.import_('Prelude'); G = curry.import_('Geo'); p = curry.eval(G.origin).one()
    f = curry.eval(G.norm1).one()
    self.assertIsInstance(f, curry.Function)
    self.assertEqual((repr(f), curry.typeof(f)), ('<Function norm1 :: Point -> Int>', 'Point -> Int'))
    self.assertEqual(curry.eval(f(p)).one(), 0)
    self.assertEqual(curry.eval(P.apply(f, p)).one(), 0)

  def test_char_and_string_values(self):
    P = curry.import_('Prelude'); c = curry.eval(P.chr(66)).one(); s = curry.eval(P.reverse('ab')).one()
    self.assertIsInstance(c, curry.Char)
    self.assertEqual(c, 'B')
    self.assertIs(type(s), str)
    self.assertEqual(s, 'ba')
    self.assertEqual((str(curry.eval(P.Just(c)).one()), curry.eval(P.ord(c)).one()), ("Just 'B'", 66))
    self.assertEqual((str(curry.eval(P.Just(s)).one()), curry.eval(P.length(s)).one()), ('Just "ba"', 2))
    self.assertEqual(str(curry.eval(P.Just(str(c))).one()), 'Just "B"')

  def test_print_type_and_hash_values(self):
    P = curry.import_('Prelude'); G = curry.import_('Geo'); p = curry.eval(G.origin).one(); q = curry.eval(G.Point(0, 0)).one()
    c = curry.eval(P.chr(66)).one(); s = curry.eval(P.reverse('ab')).one()
    self.assertEqual(curry.eval(P.show(p)).one(), 'Point 0 0')
    self.assertEqual((curry.show(p), curry.show(c), curry.show(s)), ('Point 0 0', "'B'", '"ba"'))
    self.assertEqual((curry.typeof(p), curry.typeof(c), curry.typeof(s)), ('Point', 'Char', '[Char]'))
    self.assertIn(p, {q: 1})
    self.assertEqual({(p, c): 1}[(q, curry.Char('B'))], 1)

  def test_constructor_classes(self):
    T = curry.import_('Geo')
    def total(t):
      match t:
        case T.Leaf:
          return 0
        case T.Node(l, x, r):
          return total(l) + x + total(r)
    def depth(t):
      match t:
        case T.Leaf:
          return 0
        case T.Node(l, _, r):
          return 1 + max(depth(l), depth(r))
    tree = T.Node(T.Node(T.Leaf, 1, T.Leaf), 2, T.Node(T.Leaf, 3, T.Leaf))
    self.assertIsInstance(tree, curry.info(T).types['Tree'].cls)
    self.assertIs(T.Node.datatype.cls, curry.info(T).types['Tree'].cls)
    self.assertIs(curry.info(T), getattr(T, '.info'))
    self.assertEqual(type(tree).__name__, 'Node')
    self.assertEqual(str(tree), 'Node (Node Leaf 1 Leaf) 2 (Node Leaf 3 Leaf)')
    self.assertEqual((total(tree), depth(tree)), (6, 2))
    self.assertEqual(curry.eval(tree).one(), tree)
    self.assertEqual(tree.args, (T.Node(T.Leaf, 1, T.Leaf), 2, T.Node(T.Leaf, 3, T.Leaf)))

  def test_nested_patterns(self):
    T = curry.import_('Geo')
    def describe(t):
      match t:
        case T.Node(T.Leaf, x, T.Leaf):
          return 'a single node holding %d' % x
        case T.Node(T.Node(_, a, _), b, T.Leaf):
          return 'a left-leaning node: %d above %d' % (b, a)
        case T.Node(_, x, _):
          return 'a node holding %d' % x
        case T.Leaf:
          return 'a leaf'
    tree = T.Node(T.Node(T.Leaf, 1, T.Leaf), 2, T.Node(T.Leaf, 3, T.Leaf))
    self.assertEqual(describe(tree), 'a node holding 2')
    self.assertEqual(describe(T.Node(T.Node(T.Leaf, 7, T.Leaf), 9, T.Leaf)), 'a left-leaning node: 9 above 7')
    self.assertEqual(describe(T.Leaf), 'a leaf')
    self.assertEqual(describe(T.Node(T.Leaf, 4, T.Leaf)), 'a single node holding 4')


if __name__ == '__main__':
  unittest.main()
