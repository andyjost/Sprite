'''
F08: acceptance of the recommended Python API.

Trace: alt.py and alt.{cxx,py}.out.2; line numbers include the
recorded command header when present. Each row names its flip lane.
  test_independent_and_shared_calls: alt.py 9-13; output 1-4; lane 4.
  test_sharing_prints_as_let: alt.py 14; output 5; lane 4.
  test_evaluation_keeps_term: alt.py 15-16; output 6-7; lane 4.
  test_attributes_are_fresh_terms: alt.py 17-18; output 8-9; lane 4.
  test_structural_keys: alt.py 19; output 10; lane 4.
  test_choice_sharing: alt.py 20-22; output 11-12; lane 4.
  test_variable_and_value_sharing: alt.py 23-26; output 13-14; lane 4.
  test_cyclic_list: alt.py 27-29; output 15-16; lane 4.
  test_text_preserves_sharing: alt.py 30; output 17; lane 4.
  test_term_in_python_list: alt.py 31-33; output 18-19; lane 4.

Left out: No semantic lines omitted. Harness show is replaced by unittest.

Departures and rules: No value departures. Class membership replaces the incidental
concrete class-name check at 17 (Appendix A 5991-6013).

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


class TestFlowF08(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  def test_independent_and_shared_calls(self):
    P = curry.import_('Prelude'); C = curry.import_('Coin'); t = C.coin
    self.assertEqual(list(curry.eval(C.double(C.coin))), [0, 2])
    self.assertEqual(sorted(curry.eval(P['+'](C.coin, C.coin))), [0, 1, 1, 2])
    self.assertEqual(sorted(curry.eval(P['+'](t, t))), [0, 2])
    self.assertEqual(list(curry.eval((t, t))), [(0, 0), (1, 1)])
    self.assertEqual(list(curry.eval((C.coin, C.coin))), [(0, 0), (0, 1), (1, 0), (1, 1)])

  @unittest.expectedFailure
  def test_sharing_prints_as_let(self):
    P = curry.import_('Prelude'); C = curry.import_('Coin'); t = C.coin
    self.assertEqual((str(t), repr(t)), ('coin', '<Term coin :: Int>'))
    self.assertEqual(str(P['+'](t, t)), 'let x1 = coin in x1 + x1')
    self.assertEqual(curry.show((t, t)), 'let x1 = coin in (x1,x1)')
    self.assertEqual(curry.show((C.coin, C.coin)), '(coin,coin)')

  def test_evaluation_keeps_term(self):
    C = curry.import_('Coin'); t = C.coin
    self.assertEqual(list(curry.eval(t)), [0, 1])
    self.assertEqual(list(curry.eval(t)), [0, 1])
    self.assertEqual(str(t), 'coin')
    self.assertEqual(list(curry.eval((t, 5))), [(0, 5), (1, 5)])
    self.assertEqual(list(curry.eval((t, t))), [(0, 0), (1, 1)])

  def test_attributes_are_fresh_terms(self):
    C = curry.import_('Coin'); t = C.coin
    self.assertIsInstance(t, curry.Term)
    self.assertEqual(C.coin, C.coin)
    self.assertIsNot(C.coin, C.coin)
    self.assertEqual(t, t)
    with self.assertRaises(TypeError):
      C.coin()

  def test_structural_keys(self):
    C = curry.import_('Coin')
    self.assertEqual(C.inc(1), C.inc(1))
    self.assertEqual({C.inc(1): 1}[C.inc(1)], 1)

  def test_choice_sharing(self):
    ch = curry.choice(1, 2)
    self.assertEqual(list(curry.eval((ch, ch))), [(1, 1), (2, 2)])
    self.assertEqual(list(curry.eval((curry.choice(1, 2), curry.choice(1, 2)))), [(1, 1), (1, 2), (2, 1), (2, 2)])

  def test_variable_and_value_sharing(self):
    C = curry.import_('Coin'); x = curry.free()
    self.assertEqual(curry.show(curry.eval((x, x)).one()), '(_a,_a)')
    v = next(curry.eval(C.coin))
    self.assertIs(type(v), int)
    self.assertEqual(list(curry.eval((v, v))), [(0, 0)])

  def test_cyclic_list(self):
    P = curry.import_('Prelude'); ones = curry.parse('let a = 1 : a in a')
    self.assertEqual(curry.eval(P.take(3, ones)).one(), [1, 1, 1])
    self.assertEqual(str(ones), 'let a = 1 : a in a')

  @unittest.expectedFailure
  def test_text_preserves_sharing(self):
    C = curry.import_('Coin'); t = C.coin
    self.assertEqual(list(curry.eval(curry.parse(curry.show((t, t)), imports=[C]))), [(0, 0), (1, 1)])

  def test_term_in_python_list(self):
    P = curry.import_('Prelude'); C = curry.import_('Coin'); xs = [C.coin]
    self.assertEqual(sorted(curry.eval(P['++'](xs, xs))), [[0, 0], [1, 1]])
    t = C.coin
    self.assertEqual((t.symbol.name, t.args), ('coin', ()))


if __name__ == '__main__':
  unittest.main()
