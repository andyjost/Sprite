'''
F03: acceptance of the recommended Python API.

Trace: alt.py and alt.{cxx,py}.out.2; line numbers include the
recorded command header when present. Each row names its flip lane.
  test_consume_partially: alt.py 15-18; output 2-4; lane 3.
  test_close: alt.py 19; output 5; lane 3.
  test_length_and_materialization: alt.py 20-22; output 6-7; lane 3.
  test_context_closes: alt.py 23-24; output 8-9; lane 3.
  test_no_value: alt.py 25-27; output 10-11; lane 3.
  test_many_values: alt.py 28-29; output 12; lane 3.
  test_failed_alternative: alt.py 30; output 13; lane 3.
  test_error_after_values: alt.py 31; output 14; lane 1.
  test_left_associated_error: alt.py 32; output 15; lane 1.
  test_suspension: alt.py 33; output 16; lane 1.
  test_exception_root (passes since fb437dc7, the error tree): alt.py 34-35; output 17; lane 1.

Left out: No semantic lines omitted. collect/attempt are replaced by iterator
assertions.

Departures and rules: Output 17 uses Error; Appendix A 6435-6436 renames it CurryError.
The MRO is checked by ancestry, without pinning incidental mixin order.

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


class TestFlowF03(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  def test_consume_partially(self):
    M = curry.import_('Stream'); r = curry.eval(M.three)
    self.assertIsInstance(r, curry.Results)
    self.assertEqual((next(r), next(r)), (1, 2))
    for v in r:
      self.assertEqual(v, 3)
      break
    self.assertEqual(next(r, 'end'), 'end')

  def test_close(self):
    M = curry.import_('Stream'); r = curry.eval(M.three)
    next(r)
    self.assertIsNone(r.close())
    self.assertEqual(list(r), [])

  def test_length_and_materialization(self):
    M = curry.import_('Stream')
    with self.assertRaises(TypeError):
      len(curry.eval(M.three))
    values = list(curry.eval(M.three))
    self.assertEqual(values, [1, 2, 3])
    self.assertTrue(all(type(v) is int for v in values))
    self.assertEqual(len(values), 3)

  def test_context_closes(self):
    M = curry.import_('Stream')
    with curry.eval(M.three) as r:
      self.assertEqual(next(r), 1)
    self.assertEqual(list(r), [])

  def test_no_value(self):
    M = curry.import_('Stream')
    self.assertEqual(list(curry.eval(M.nothing)), [])
    self.assertIsNone(next(curry.eval(M.nothing), None))
    with self.assertRaises(curry.NoValueError) as caught:
      curry.eval(M.nothing).one()
    self.assertEqual(str(caught.exception), 'No value found: nothing')

  def test_many_values(self):
    M = curry.import_('Stream')
    with self.assertRaises(curry.ManyValuesError) as caught:
      curry.eval(M.three).one()
    self.assertEqual(str(caught.exception), 'more than one value: three has 1 and 2')

  def test_failed_alternative(self):
    M = curry.import_('Stream')
    values = list(curry.eval(M.partial))
    self.assertEqual(values, [1, 2])
    self.assertTrue(all(type(v) is int for v in values))

  def test_error_after_values(self):
    M = curry.import_('Stream'); r = curry.eval(M.mixed)
    self.assertEqual([next(r) for _ in range(1)], [1])
    with self.assertRaises(curry.EvaluationError) as caught:
      next(r)
    self.assertIsInstance(caught.exception, Exception)
    self.assertEqual(str(caught.exception), 'boom')
    self.assertEqual(list(r), [])

  def test_left_associated_error(self):
    M = curry.import_('Stream'); r = curry.eval(M.mixedL)
    self.assertEqual([next(r) for _ in range(2)], [2, 1])
    with self.assertRaises(curry.EvaluationError) as caught:
      next(r)
    self.assertIsInstance(caught.exception, Exception)
    self.assertEqual(str(caught.exception), 'boom')
    self.assertEqual(list(r), [])

  @unittest.expectedFailure
  def test_suspension(self):
    P = curry.import_('Prelude')
    r = curry.eval(P['=:='](P['+'](curry.free(), 1), 3))
    with self.assertRaises(curry.SuspensionError) as caught:
      next(r)
    self.assertEqual(str(caught.exception), 'Evaluation suspended: _a + 1 =:= 3')
    self.assertEqual(list(r), [])

  def test_exception_root(self):
    M = curry.import_('Stream')
    try:
      list(curry.eval(M.mixed))
    except Exception as error:
      self.assertIsInstance(error, curry.EvaluationError)
      self.assertIsInstance(error, curry.CurryError)
    else:
      self.fail('mixed must raise')


if __name__ == '__main__':
  unittest.main()
