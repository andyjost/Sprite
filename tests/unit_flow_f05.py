'''
F05: acceptance of the recommended Python API.

Trace: alt.py and alt.{cxx,py}.out.3; line numbers include the
recorded command header when present. Each row names its flip lane.
  test_text_answers: alt.py 16-19; output 2-5; lane 3.
  test_annotation_before_clause: alt.py 20; output 6; lane 3.
  test_annotation_after_clause: alt.py 21; output 7; lane 4.
  test_comment_makes_clause_local: alt.py 22; output 8; lane 3.
  test_list_constraint: alt.py 23; output 9; lane 3.
  test_binding_in_result_type: alt.py 24; output 10; lane 3.
  test_narrow_bool: alt.py 26; output 12; lane 3.
  test_ambiguous_type: alt.py 25; output 11; lane 3.
  test_types_and_bare_text: alt.py 27-29; output 13-14; lane 4.
  test_same_answers_as_expression: alt.py 30-31; output 15; lane 3.
  test_parsed_term_composes: alt.py 32-34; output 16-17; lane 4.

Left out: No semantic lines omitted. show/goal harness is replaced by direct assertions.

Departures and rules: Output .3:11 reaches typeof after evaluating the goal; the test
checks those values too, as the stage C correction specifies. No error position from the
facade wrapper is frozen (Appendix A 6488-6496).

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


class TestFlowF05(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  @unittest.expectedFailure
  def test_text_answers(self):
    R = curry.import_('Rule'); g = curry.parse('rule "a" ins where ins free', imports=[R])
    a = next(curry.solve(g))
    self.assertIsInstance(a, curry.Answer)
    self.assertEqual(repr(a), 'Answer(value=\'cmd1\', bindings={ins=["x"]})')
    self.assertEqual(a.value, 'cmd1')
    self.assertEqual(str(a.bindings), '{ins=["x"]}')
    self.assertEqual(a.bindings['ins'], ['x'])
    self.assertEqual([(cmd, b['ins']) for cmd, b in curry.solve(g)],
        [('cmd1', ['x']), ('cmd2', ['y', 'z'])])
    self.assertEqual([str(a) for a in curry.solve(g)], ['{ins=["x"]} "cmd1"', '{ins=["y","z"]} "cmd2"'])
    self.assertEqual(list(curry.eval(g)), ['cmd1', 'cmd2'])
    self.assertEqual(curry.typeof(g), '[Char]')

  @unittest.expectedFailure
  def test_annotation_before_clause(self):
    R = curry.import_('Rule')
    g = curry.parse('rule "a" ins :: String where ins free', imports=[R])
    self.assertEqual([str(a) for a in curry.solve(g)], ['{ins=["x"]} "cmd1"', '{ins=["y","z"]} "cmd2"'])
    self.assertEqual(list(curry.eval(g)), ['cmd1', 'cmd2'])
    self.assertEqual(curry.typeof(g), '[Char]')

  @unittest.expectedFailure
  def test_annotation_after_clause(self):
    R = curry.import_('Rule')
    with self.assertRaises(curry.CompileError):
      curry.parse('rule "a" ins where ins free :: String', imports=[R])

  @unittest.expectedFailure
  def test_comment_makes_clause_local(self):
    R = curry.import_('Rule')
    g = curry.parse('rule "a" ins where ins free -- the rule', imports=[R])
    self.assertEqual([str(a) for a in curry.solve(g)], ['"cmd1"', '"cmd2"'])
    self.assertEqual(list(curry.eval(g)), ['cmd1', 'cmd2'])
    self.assertEqual(curry.typeof(g), '[Char]')

  @unittest.expectedFailure
  def test_list_constraint(self):
    g = curry.parse('xs ++ [3] =:= [1,2,3] where xs free')
    self.assertEqual([str(a) for a in curry.solve(g)], ['{xs=[1,2]} True'])
    self.assertEqual(list(curry.eval(g)), [True])
    self.assertEqual(curry.typeof(g), 'Bool')

  @unittest.expectedFailure
  def test_binding_in_result_type(self):
    g = curry.parse('(xs =:= [1 :: Int], [0 :: Int]) where xs free')
    self.assertEqual([str(a) for a in curry.solve(g)], ['{xs=[1]} (True,[0])'])
    self.assertEqual(list(curry.eval(g)), [(True, [0])])
    self.assertEqual(curry.typeof(g), '(Bool, [Int])')

  @unittest.expectedFailure
  def test_narrow_bool(self):
    g = curry.parse('not b where b free')
    self.assertEqual([str(a) for a in curry.solve(g)], ['{b=False} True', '{b=True} False'])
    self.assertEqual(list(curry.eval(g)), [True, False])
    self.assertEqual(curry.typeof(g), 'Bool')

  @unittest.expectedFailure
  def test_ambiguous_type(self):
    g = curry.parse('x =:= y where x, y free')
    self.assertEqual([str(a) for a in curry.solve(g)], ['{x=x, y=x} True'])
    self.assertEqual(list(curry.eval(g)), [True])
    with self.assertRaises(curry.CompileError) as caught:
      curry.typeof(g)
    self.assertIn('Ambiguous type variable', str(caught.exception))

  @unittest.expectedFailure
  def test_types_and_bare_text(self):
    self.assertEqual(curry.typeof(curry.parse('xs ++ ys where xs, ys free')), 'Data a => [a]')
    self.assertEqual((curry.typeof('a'), curry.typeof('ab')), ('[Char]', '[Char]'))
    with self.assertRaises(curry.ConversionError):
      curry.eval('rule "a" ins where ins free')

  @unittest.expectedFailure
  def test_same_answers_as_expression(self):
    R = curry.import_('Rule'); ins = curry.free('ins')
    g = curry.parse('rule "a" ins where ins free', imports=[R])
    self.assertEqual(list(curry.solve(R.rule('a', ins))), list(curry.solve(g)))

  @unittest.expectedFailure
  def test_parsed_term_composes(self):
    P = curry.import_('Prelude'); R = curry.import_('Rule')
    g = curry.parse('rule "a" ins where ins free', imports=[R])
    self.assertEqual(repr(g), '<Term rule "a" ins where ins free :: [Char]>')
    self.assertEqual(str(g), 'rule "a" ins where ins free')
    self.assertEqual(list(g.free_vars), ['ins'])
    self.assertIsInstance(g.free_vars['ins'], curry.Var)
    self.assertEqual(list(curry.eval(P.length(g))), [4, 4])


if __name__ == '__main__':
  unittest.main()
