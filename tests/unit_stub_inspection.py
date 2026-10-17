'''
Inspection: frozen acceptance of Appendix A of python-api-review2.md.

Each row maps a test to the review's lines and the flip lane of
python-api-implementation-plan.md. Section 12 amends metadata access.
  test_typeof_example: lines 6402-6403; lane 2.
  test_show_example: lines 6421-6422; lane 1.
  test_typeof_defaulted_uses_repl_table: lines 6396-6400; lane 2.
  test_typeof_text_and_value_agree: lines 6396-6398; lane 2.
  test_typeof_refuses_repl_refusal (a parsed text: CompileError, as stage C's rule and F05 say; corrected by the reviewer 2026-10-16): lines 6399; lane 2.
  test_typeof_answer_is_value_type: lines 6394; lane 2.
  test_show_constructor_negative_argument: lines 6408-6410; lane 1.
  test_show_operator_precedence: lines 6410-6411; lane 1.
  test_show_variables_numbered_per_text: lines 6411-6413; lane 1.
  test_show_shared_reducible_subterm: lines 6413; lane 4d.
  test_show_equals_str_for_curry_objects: lines 6414-6415; lane 1.
  test_show_empty_string_and_partial_operator_departures: lines 6415-6418; lane 1.

Examples left out: none. Setup prompts have their own tests; result
tests repeat their setup so they can run independently.
'''
import cytest # from ./lib; must be first
import curry
import unittest
import os

FLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'curry', 'flows')


def setUpModule():
  curry.path.insert(0, FLOW_PATH)


class TestStubInspection(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  def test_typeof_example(self):
    Coin = curry.import_('Coin')
    self.assertEqual(
        (curry.typeof(1), curry.typeof(Coin.inc(1)), curry.typeof('a'), curry.typeof(curry.free('x')))
      , ('Num a => a', 'Int', '[Char]', 'Data a => a')
      )

  @unittest.expectedFailure
  def test_show_example(self):
    self.assertEqual(
        (curry.show([1, 2]), curry.show('ab'), curry.show((curry.Char('a'), 1)), curry.show(''))
      , ('[1,2]', '"ab"', "('a',1)", '""')
      )

  def test_typeof_defaulted_uses_repl_table(self):
    self.assertEqual(curry.typeof(1, defaulted=True), 'Int')
    self.assertEqual(curry.typeof(curry.term(1), defaulted=True), 'Int')

  def test_typeof_text_and_value_agree(self):
    self.assertEqual(curry.typeof('ab'), '[Char]')
    self.assertEqual(curry.typeof(curry.parse('"ab"')), '[Char]')

  @unittest.expectedFailure
  def test_typeof_refuses_repl_refusal(self):
    with self.assertRaises(curry.CompileError):
      curry.typeof(curry.parse('x =:= y where x, y free'))

  @unittest.expectedFailure
  def test_typeof_answer_is_value_type(self):
    a = curry.solve(curry.term(1, type='Int')).one()
    self.assertEqual(curry.typeof(a), 'Int')

  @unittest.expectedFailure
  def test_show_constructor_negative_argument(self):
    P = curry.import_('Prelude')
    self.assertEqual(curry.show(P.Just(-1)), 'Just (-1)')

  @unittest.expectedFailure
  def test_show_operator_precedence(self):
    Coin = curry.import_('Coin')
    self.assertEqual(curry.show(Coin.inc(curry.choice(1, 2))), 'inc (1 ? 2)')

  @unittest.expectedFailure
  def test_show_variables_numbered_per_text(self):
    a = curry.free()
    b = curry.free()
    x = curry.free('x')
    self.assertEqual(curry.show((b, a, b, x)), '(_a,_b,_a,x)')
    self.assertEqual(curry.show(a), '_a')

  @unittest.expectedFailure
  def test_show_shared_reducible_subterm(self):
    Coin = curry.import_('Coin')
    P = curry.import_('Prelude')
    c = Coin.coin
    self.assertEqual(curry.show(P['+'](c, c)), 'let x1 = coin in x1 + x1')

  @unittest.expectedFailure
  def test_show_equals_str_for_curry_objects(self):
    Coin = curry.import_('Coin')
    t = Coin.inc(1)
    self.assertEqual(curry.show(t), str(t))
    self.assertEqual(str([1, 2]), '[1, 2]')

  @unittest.expectedFailure
  def test_show_empty_string_and_partial_operator_departures(self):
    P = curry.import_('Prelude')
    self.assertEqual(curry.show(curry.term('', type='[Char]')), '""')
    self.assertEqual(curry.show(P['+'](1)), '(+) 1')


if __name__ == '__main__':
  unittest.main()
