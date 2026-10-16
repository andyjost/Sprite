'''
F14: acceptance of the recommended Python API.

Trace: alt.py and alt.{cxx,py}.out.2; line numbers include the
recorded command header when present. Each row names its flip lane.
  test_answer_line: alt.py 5-6; output 2; lane 3.
  test_values_and_free_variable: alt.py 7; output 3; lane 3.
  test_no_value: alt.py 8-10; output 4-5; lane 3.
  test_evaluation_error: alt.py 11-12; output 6; lane 1.
  test_suspension: alt.py 13-14; output 7; lane 1.
  test_io_payload: alt.py 15; output 8-9; lane 3.
  test_types: alt.py 16; output 10; lane 3.
  test_flag_names: alt.py 17; output 11; lane 5.

Left out: Omit 18 (# FACADE) and 19 (not-run notice), output 12: REPL and sprite-exec
belong to lane 8. Keep every API line.

Departures and rules: Appendix A 6435-6436 renames Error to CurryError. IO runs in a
child process to capture both runtime streams. API shapes and exact printed Answer and
IO lines follow the recorded output.

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


class TestFlowF14(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  @unittest.expectedFailure
  def test_answer_line(self):
    T = curry.import_('Tools')
    g = curry.parse('xs ++ [3] =:= [1,2,3] where xs free', imports=[T])
    a = curry.solve(g).one()
    self.assertIsInstance(a, curry.Answer)
    self.assertEqual(str(a), '{xs=[1,2]} True')
    self.assertEqual(repr(a), 'Answer(value=True, bindings={xs=[1,2]})')
    self.assertIs(a.value, True)
    self.assertEqual(a.bindings['xs'], [1, 2])

  @unittest.expectedFailure
  def test_values_and_free_variable(self):
    T = curry.import_('Tools'); g = curry.parse('xs ++ [3] =:= [1,2,3] where xs free', imports=[T])
    self.assertEqual(list(curry.eval(g)), [True])
    self.assertEqual(list(curry.eval(T.bound)), [True])
    v = curry.eval(T.freegoal).one()
    self.assertIsInstance(v[0], curry.Var)
    self.assertEqual(v[1], 1)
    self.assertEqual(curry.show(v), '(_a,1)')

  @unittest.expectedFailure
  def test_no_value(self):
    T = curry.import_('Tools')
    self.assertEqual(list(curry.eval(T.nothing)), [])
    with self.assertRaises(curry.NoValueError) as caught:
      curry.eval(T.nothing).one()
    self.assertEqual(str(caught.exception), 'No value found: nothing')

  @unittest.expectedFailure
  def test_evaluation_error(self):
    T = curry.import_('Tools')
    with self.assertRaises(curry.CurryError) as caught:
      curry.eval(T.boom).one()
    self.assertIsInstance(caught.exception, curry.EvaluationError)
    self.assertIsInstance(caught.exception, Exception)
    self.assertEqual(str(caught.exception), 'boom')

  @unittest.expectedFailure
  def test_suspension(self):
    T = curry.import_('Tools')
    with self.assertRaises(curry.SuspensionError) as caught:
      list(curry.eval(T.suspend))
    self.assertEqual(str(caught.exception), 'Evaluation suspended: suspend')

  @unittest.expectedFailure
  def test_io_payload(self):
    code = """
import curry
curry.path.insert(0, %r)
T = curry.import_('Tools')
values = list(curry.eval(T.hello))
assert values == [()]
assert type(values[0]) is tuple
print(repr(values))
""" % FLOW_PATH
    proc = cytest.run_in_subprocess(code, timeout=120)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout, 'hello\n[()]\n')

  @unittest.expectedFailure
  def test_types(self):
    T = curry.import_('Tools'); g = curry.parse('xs ++ [3] =:= [1,2,3] where xs free', imports=[T])
    self.assertEqual((curry.typeof(T.freegoal), curry.typeof(g), curry.typeof(T.bound)), ('(Int, Int)', 'Bool', 'Bool'))

  def test_flag_names(self):
    self.assertEqual(sorted(curry.flags), [
        'backend', 'checker', 'debug', 'defaultconverter', 'inline_budget'
      , 'interpret', 'keep_temp_files', 'lazycompile', 'postmortem'
      , 'recursion_limit', 'rotation', 'stack_limit', 'step_budget'
      , 'telemetry_interval', 'trace', 'typed_expr'
      ])


if __name__ == '__main__':
  unittest.main()
