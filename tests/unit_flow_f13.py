'''
F13: acceptance of the recommended Python API.

Trace: alt.py and alt.{cxx,py}.out.2; line numbers include the
recorded command header when present. Each row names its flip lane.
  test_choice_protocol: alt.py 10-12; output 2-4; lane 4.
  test_anonymous_placeholder: alt.py 13-14; output 5-6; lane 3.
  test_structural_keys: alt.py 15-16; output 7; lane 4.
  test_arithmetic_and_infix: alt.py 17; output 8; lane 4.
  test_variable_keys_and_choice: alt.py 18; output 9; lane 4.
  test_fork_precedence: alt.py 19; output 10; lane 4.
  test_equations_and_comparison: alt.py 20-21; output 11-12; lane 4.

Left out: No semantic lines omitted. The fork-only syntax of 10-12 is expressed through
ChoiceType and choice hooks; 19 is parsed inside the method so the test module imports
on stock Python 3.14.

Departures and rules: No value departures. Availability of ChoiceType and the question-
mark parser is an open environment point; lane 4 markers cannot flip for those two steps
until the test interpreter supplies the fork.

Lanes refer to the Python API implementation plan. Tests import curry,
the package. Missing proposed names are only used inside test methods.
'''
import cytest # from ./lib; must be first
import curry
import unittest
import os
import types

FLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'curry', 'flows')


def setUpModule():
  curry.path.insert(0, FLOW_PATH)


class TestFlowF13(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  @unittest.expectedFailure
  def test_choice_protocol(self):
    I = curry.import_('Items')
    self.assertEqual(list(curry.eval(types.ChoiceType(1, 2))), [1, 2])
    self.assertEqual(list(curry.eval(I.inc(1).__choice__(2))), [2, 2])
    self.assertEqual(list(curry.eval(I.inc(1).__rchoice__(2))), [2, 2])
    self.assertEqual(repr(I.inc(1).__choice__(2)), '<Term inc 1 ? 2 :: Int>')
    self.assertEqual(repr(I.inc.__choice__(I.dbl)), '<Term inc ? dbl :: Int -> Int>')
    self.assertEqual(repr(curry.choice(1, 2)), '<Term 1 ? 2 :: Num a => a>')
    self.assertEqual(str(I.inc(types.ChoiceType(1, 2))), 'inc (1 ? 2)')
    self.assertEqual(sorted(curry.eval(I.inc(types.ChoiceType(1, 2)))), [2, 3])
    self.assertEqual(sorted(curry.eval(I.applyAll([I.inc, I.dbl], types.ChoiceType(1, 2)))), [[2, 2], [3, 4]])

  @unittest.expectedFailure
  def test_anonymous_placeholder(self):
    R = curry.import_('Rule'); anonymous = curry.anonymous
    self.assertEqual(list(curry.eval(R.rule('a', anonymous))), ['cmd1', 'cmd2'])
    self.assertEqual([dict(a.bindings) for a in curry.solve(R.rule('a', anonymous))], [{}, {}])
    v = curry.eval((anonymous, anonymous)).one()
    self.assertIsInstance(v[0], curry.Var)
    self.assertIsInstance(v[1], curry.Var)
    self.assertIsNot(v[0], v[1])
    self.assertEqual(curry.show(v), '(_a,_b)')

  def test_structural_keys(self):
    I = curry.import_('Items'); C = curry.import_('Coin'); t = I.inc(1)
    table = {t: 'one', C.coin: 'coin'}
    self.assertEqual(t, t)
    self.assertEqual(t, I.inc(1))
    self.assertEqual(hash(t), hash(I.inc(1)))
    self.assertEqual((table[I.inc(1)], table[C.coin]), ('one', 'coin'))
    self.assertIsNot(t, I.inc(1))

  @unittest.expectedFailure
  def test_arithmetic_and_infix(self):
    I = curry.import_('Items'); C = curry.import_('Coin'); t = I.inc(1)
    self.assertNotEqual(t, 2)
    with self.assertRaises(TypeError):
      bool(t)
    self.assertEqual(str(t + 2 * C.coin), 'inc 1 + 2 * coin')
    self.assertEqual(str(curry.term([1, 2]).__infix__('++', [3])), '[1,2] ++ [3]')

  @unittest.expectedFailure
  def test_variable_keys_and_choice(self):
    x = curry.free('x')
    self.assertEqual(x, x)
    self.assertNotEqual(x, curry.free('x'))
    self.assertEqual({x: 1}[x], 1)
    self.assertEqual(repr(x.__choice__(1)), '<Term x ? 1 :: (Data a, Num a) => a>')

  @unittest.expectedFailure
  def test_fork_precedence(self):
    I = curry.import_('Items')
    self.assertEqual(repr(eval('1 ? 2 == 1 ? 2')), 'ChoiceType(1, ChoiceType(False, 2))')
    with self.assertRaises(curry.ConversionError):
      eval('I.inc(1) ? 2 == 2')

  @unittest.expectedFailure
  def test_equations_and_comparison(self):
    P = curry.import_('Prelude'); I = curry.import_('Items'); t = I.inc(1)
    eq = P['=='](t, 2)
    self.assertEqual(str(eq), 'inc 1 == 2')
    self.assertIs(curry.eval(eq).one(), True)
    self.assertEqual((P['=:='].symbol.fixity, P['=='].symbol.fixity), ('infix 4', 'infix 4'))
    with self.assertRaises(TypeError):
      t < I.inc(2)
    self.assertEqual(str(P['<'](t, I.inc(2))), 'inc 1 < inc 2')


if __name__ == '__main__':
  unittest.main()
