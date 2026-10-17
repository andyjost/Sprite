'''
F02: acceptance of the recommended Python API.

Trace: alt.py and alt.{cxx,py}.out.2; line numbers include the
recorded command header when present. Each row names its flip lane.
  test_symbols_in_lists: alt.py 13-15; output 2-4; lane 4.
  test_constructor_tree: alt.py 16-18; output 5-6; lane 4.
  test_list_is_never_application: alt.py 19; output 7; lane 4.
  test_function_value: alt.py 20-24, 33; output 8-11, 20; lane 3.
  test_partial_application: alt.py 25-27; output 12-14; lane 4.
  test_apply_result: alt.py 28-29; output 15-16; lane 4.
  test_arity_at_call: alt.py 30-32; output 17-19; lane 4.
  test_operator_partial_printing: alt.py appendix 6129-6138; output decision (g); lane 1.

Left out: No semantic lines omitted. Harness lines 1-12 are replaced by unittest.

Departures and rules: Constructor classes follow A26. The operator partial case is added
by decision (g), Appendix A 6129-6138. Conversion messages are not frozen (README
approximation).

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


class TestFlowF02(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  @unittest.expectedFailure
  def test_symbols_in_lists(self):
    I = curry.import_('Items')
    self.assertEqual(list(curry.eval(I.countItems([I.A, I.B]))), [2])
    self.assertEqual(list(curry.eval(I.applyAll([I.inc, I.dbl], 5))), [[6, 10]])
    self.assertEqual(curry.typeof(curry.term([I.inc, I.dbl])), '[Int -> Int]')

  @unittest.expectedFailure
  def test_constructor_tree(self):
    P = curry.import_('Prelude'); G = curry.import_('Geo')
    tree = G.Node(G.Node(G.Leaf, 1, G.Leaf), 2, G.Leaf)
    self.assertEqual(str(tree), 'Node (Node Leaf 1 Leaf) 2 Leaf')
    self.assertEqual(list(curry.eval(P.show(tree))), ['Node (Node Leaf 1 Leaf) 2 Leaf'])

  @unittest.expectedFailure
  def test_list_is_never_application(self):
    I = curry.import_('Items')
    with self.assertRaises(curry.ConversionError):
      list(curry.eval([I.inc, 1]))

  @unittest.expectedFailure
  def test_function_value(self):
    P = curry.import_('Prelude'); I = curry.import_('Items')
    f = curry.eval(I.inc).one()
    self.assertIsInstance(f, curry.Function)
    self.assertEqual((repr(f), str(f), curry.typeof(f)),
        ('<Function inc :: Int -> Int>', 'inc', 'Int -> Int'))
    self.assertEqual(list(curry.eval(P.apply(f, 41))), [42])
    self.assertEqual(list(curry.eval(f(41))), [42])
    self.assertEqual(list(curry.eval(P.map(I.inc, [1, 2]))), [[2, 3]])
    self.assertEqual(list(curry.eval(I.inc)), [f])

  @unittest.expectedFailure
  def test_partial_application(self):
    P = curry.import_('Prelude'); I = curry.import_('Items')
    t = P.map(I.inc)
    self.assertEqual(str(t), 'map inc')
    self.assertEqual(str(curry.eval(t).one()), 'map inc')
    self.assertEqual(curry.typeof(t), '[Int] -> [Int]')

  @unittest.expectedFailure
  def test_apply_result(self):
    P = curry.import_('Prelude'); I = curry.import_('Items')
    t = P.id(I.inc, 1)
    self.assertEqual(str(t), 'apply (id inc) 1')
    self.assertEqual(list(curry.eval(t)), [2])

  def test_arity_at_call(self):
    I = curry.import_('Items')
    with self.assertRaises(curry.ArityError):
      I.inc(1, 2)
    with self.assertRaises(curry.ArityError):
      I.A(1)
    with self.assertRaises(TypeError):
      I.inc()

  @unittest.expectedFailure
  def test_operator_partial_printing(self):
    P = curry.import_('Prelude')
    f = curry.eval(P['+'](1)).one()
    self.assertIsInstance(f, curry.Function)
    self.assertEqual(str(f), '(+) 1')
    self.assertEqual(curry.show(f), '(+) 1')


if __name__ == '__main__':
  unittest.main()
