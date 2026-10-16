'''
F04: acceptance of the recommended Python API.

Trace: alt.py and alt.{cxx,py}.out.2; line numbers include the
recorded command header when present. Each row names its flip lane.
  test_values_and_answers: alt.py 10-15; output 2-6; lane 3.
  test_anonymous_answers: alt.py 16, 27-28; output 7, 15-16; lane 3.
  test_unbound_after_goal: alt.py 17-18; output 8-9; lane 3.
  test_alias_is_private_to_goal: alt.py 19-21; output 10-11; lane 3.
  test_variable_identity: alt.py 22-23; output 12; lane 3.
  test_duplicate_names_at_call: alt.py 24-25; output 13; lane 3.
  test_variable_type: alt.py 26; output 14; lane 3.
  test_second_type_rejected_at_call: alt.py 29; output decision (b); lane 3.
  test_stale_variable: alt.py 30-34; output 17-18; lane 5.

Left out: No semantic lines omitted. Line 29 becomes a construction-only regression.

Departures and rules: Decision (b), Appendix A 5919-5927: a second incompatible type
must raise CurryTypeError at the call. Output 14 still prints Data a => a after the rule
goal; the test checks that initial scheme and then [[Char]], since the first concrete
goal fixes the marker type. This discrepancy is listed in the report. Output 16 uses
Python tuple spacing; show uses the Curry spacing of Appendix A 6410-6423, and variables
are also checked by identity.

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


class TestFlowF04(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  @unittest.expectedFailure
  def test_values_and_answers(self):
    R = curry.import_('Rule'); ins = curry.free('ins')
    self.assertEqual(list(curry.eval(R.rule('a', ins))), ['cmd1', 'cmd2'])
    a = next(curry.solve(R.rule('a', ins)))
    self.assertIsInstance(a, curry.Answer)
    self.assertIsInstance(a.bindings, curry.Bindings)
    self.assertEqual((str(a), len(a), a.value), ('{ins=["x"]} "cmd1"', 2, 'cmd1'))
    self.assertEqual(a.bindings['ins'], ['x'])
    self.assertEqual(a.bindings[ins], ['x'])
    self.assertEqual([(cmd, b[ins]) for cmd, b in curry.solve(R.rule('a', ins))],
        [('cmd1', ['x']), ('cmd2', ['y', 'z'])])

  @unittest.expectedFailure
  def test_anonymous_answers(self):
    R = curry.import_('Rule')
    self.assertEqual([str(a) for a in curry.solve(R.rule('a', curry.free()))], ['"cmd1"', '"cmd2"'])
    self.assertEqual(list(curry.eval(R.rule('a', curry.anonymous))), ['cmd1', 'cmd2'])
    x, y = curry.eval((curry.anonymous, curry.anonymous)).one()
    self.assertIsInstance(x, curry.Var)
    self.assertIsNot(x, y)
    self.assertEqual(curry.show((x, y)), '(_a,_b)')

  @unittest.expectedFailure
  def test_unbound_after_goal(self):
    P = curry.import_('Prelude'); R = curry.import_('Rule'); ins = curry.free('ins')
    list(curry.eval(R.rule('a', ins)))
    self.assertEqual((repr(ins), str(ins)), ('ins', 'ins'))
    self.assertIs(curry.eval(ins).one(), ins)
    self.assertEqual(str(next(curry.solve(P['=:='](ins, ['q'])))), '{ins=["q"]} True')

  @unittest.expectedFailure
  def test_alias_is_private_to_goal(self):
    P = curry.import_('Prelude'); ins = curry.free('ins'); y = curry.free('y')
    a = next(curry.solve(P['=:='](ins, y)))
    self.assertEqual(str(a), '{ins=ins, y=ins} True')
    self.assertIs(a.bindings[ins], ins)
    self.assertIs(a.bindings[y], ins)
    a = next(curry.solve((ins, y)))
    self.assertEqual(str(a), '{ins=ins, y=y} (ins,y)')
    self.assertIs(a.value[0], ins)
    self.assertIs(a.value[1], y)

  @unittest.expectedFailure
  def test_variable_identity(self):
    ins = curry.free('ins')
    self.assertFalse(curry.free('x') == curry.free('x'))
    self.assertEqual(ins, ins)
    self.assertFalse(curry.free() == curry.free())

  @unittest.expectedFailure
  def test_duplicate_names_at_call(self):
    x1, x2 = curry.free('x'), curry.free('x')
    with self.assertRaises(curry.CurryTypeError):
      curry.solve((x1, x2))

  @unittest.expectedFailure
  def test_variable_type(self):
    ins = curry.free('ins')
    self.assertEqual(curry.typeof(ins), 'Data a => a')
    R = curry.import_('Rule')
    list(curry.eval(R.rule('a', ins)))
    self.assertEqual(curry.typeof(ins), '[[Char]]')

  @unittest.expectedFailure
  def test_second_type_rejected_at_call(self):
    P = curry.import_('Prelude'); ins = curry.free('ins')
    next(curry.solve(P['=:='](ins, ['q'])))
    with self.assertRaises(curry.CurryTypeError):
      P['=:='](ins, 1)

  @unittest.expectedFailure
  def test_stale_variable(self):
    ins = curry.free('ins'); curry.reset(); R = curry.import_('Rule')
    with self.assertRaises(curry.StaleError):
      list(curry.eval(R.rule('a', ins)))
    with self.assertRaises(curry.StaleError):
      curry.eval(ins).one()


if __name__ == '__main__':
  unittest.main()
