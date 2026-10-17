'''
F12: acceptance of the recommended Python API.

Trace: alt.py and alt.{cxx,py}.out.2; line numbers include the
recorded command header when present. Each row names its flip lane.
  test_type_error_at_build: alt.py 18; output 2-3; lane 1.
  test_error_at_next: alt.py 19; output 4-5; lane 1.
  test_failure_and_one: alt.py 20-21; output 6-8; lane 3.
  test_suspension_at_next: alt.py 22; output 9-10; lane 1.
  test_file_error_at_next: alt.py 23; output 11-12; lane 1.
  test_user_io_error_at_next: alt.py 24; output 13-14; lane 1.
  test_overflow_at_next: alt.py 25; output 15-16; lane 1.
  test_literal_overflow_at_build: alt.py 26; output 17-18; lane 1.
  test_division_by_zero_at_next: alt.py 27; output 19-20; lane 1.
  test_invalid_flags_at_call: alt.py 28-29; output 21-22; lane 5.
  test_missing_modules_at_build: alt.py 30-31; output 23-25; lane 1.
  test_error_tree: alt.py 32-35; output 26; lane 1.

Left out: No fault omitted. The cell harness is replaced by assertions at build, eval
and next. Truncated conversion messages and wrapper coordinates are not frozen: the
facade README marks message translation approximate.

Departures and rules: Appendix A 6435-6436 renames Error to CurryError. Outputs 11-14
become CurryFileNotFoundError/CurryIOError (6515-6519), including filename and standard
mixins. Outputs 21-22 become FlagError (6565-6566), rather than the README
approximations TypeError/_FlagValueError. The literal overflow is IntOverflowError on
both routes (6479-6486).

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


class TestFlowF12(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  def test_type_error_at_build(self):
    P = curry.import_('Prelude')
    with self.assertRaises(curry.ConversionError) as caught:
      P['not'](1)
    self.assertIsInstance(caught.exception, curry.CurryTypeError)
    self.assertIsInstance(caught.exception, TypeError)
    self.assertIsInstance(caught.exception, curry.CurryError)
    with self.assertRaises(curry.CompileError):
      curry.parse('not 1')

  def test_error_at_next(self):
    P = curry.import_('Prelude')
    for g in (P.error('boom'), curry.parse('error "boom"')):
      r = curry.eval(g)
      with self.assertRaises(curry.EvaluationError) as caught:
        next(r)
      self.assertIsInstance(caught.exception, curry.CurryError)
      self.assertIsInstance(caught.exception, Exception)
      self.assertEqual(str(caught.exception), 'boom')

  def test_failure_and_one(self):
    P = curry.import_('Prelude')
    self.assertEqual(list(curry.eval(P.failed)), [])
    self.assertEqual(list(curry.eval(curry.parse('failed'))), [])
    with self.assertRaises(curry.NoValueError) as caught:
      curry.eval(P.failed).one()
    self.assertIsInstance(caught.exception, LookupError)

  def test_suspension_at_next(self):
    P = curry.import_('Prelude')
    expr = P['=:='](P['+'](curry.free(), 1), 3)
    text = curry.parse('x + 1 =:= 3 where x free')
    for g, message in [(expr, 'Evaluation suspended: _a + 1 =:= 3'),
        (text, 'Evaluation suspended: x + 1 =:= 3 where x free')]:
      r = curry.eval(g)
      with self.assertRaises(curry.SuspensionError) as caught:
        next(r)
      self.assertIsInstance(caught.exception, curry.EvaluationError)
      self.assertIsInstance(caught.exception, curry.CurryError)
      self.assertEqual(str(caught.exception), message)

  def test_file_error_at_next(self):
    P = curry.import_('Prelude')
    for g in (P.readFile('/nosuch'), curry.parse('readFile "/nosuch"')):
      r = curry.eval(g)
      with self.assertRaises(curry.CurryFileNotFoundError) as caught:
        next(r)
      self.assertIsInstance(caught.exception, FileNotFoundError)
      self.assertIsInstance(caught.exception, curry.CurryIOError)
      self.assertIsInstance(caught.exception, curry.EvaluationError)
      self.assertEqual(caught.exception.filename, '/nosuch')

  def test_user_io_error_at_next(self):
    P = curry.import_('Prelude')
    for g in (P.ioError(P.userError('x')), curry.parse('ioError (userError "x")')):
      r = curry.eval(g)
      with self.assertRaises(curry.CurryIOError) as caught:
        next(r)
      self.assertIsInstance(caught.exception, OSError)
      self.assertIsInstance(caught.exception, curry.EvaluationError)
      self.assertEqual(str(caught.exception), 'user error: x')

  def test_overflow_at_next(self):
    P = curry.import_('Prelude')
    expr = P['+'](curry.term(2**63 - 1, type='Int'), 1)
    for g in (expr, curry.parse('9223372036854775807 + 1')):
      r = curry.eval(g)
      with self.assertRaises(curry.IntOverflowError) as caught:
        next(r)
      self.assertIsInstance(caught.exception, OverflowError)
      self.assertIsInstance(caught.exception, curry.CurryError)
      self.assertEqual(str(caught.exception), 'integer overflow: 9223372036854775807 + 1')

  def test_literal_overflow_at_build(self):
    P = curry.import_('Prelude')
    with self.assertRaises(curry.IntOverflowError):
      P['+'](2**63, 1)
    with self.assertRaises(curry.IntOverflowError):
      curry.parse('9223372036854775808 + 1')

  def test_division_by_zero_at_next(self):
    P = curry.import_('Prelude')
    for g in (P.div(1, 0), curry.parse('div 1 0')):
      r = curry.eval(g)
      with self.assertRaises(curry.DivisionByZeroError) as caught:
        next(r)
      self.assertIsInstance(caught.exception, ZeroDivisionError)
      self.assertIsInstance(caught.exception, curry.EvaluationError)
      self.assertEqual(str(caught.exception), 'division by zero: div 1 0')

  def test_invalid_flags_at_call(self):
    for flags in ({'nosuch': 1}, {'rotation': 'abc'}):
      with self.assertRaises(curry.FlagError) as caught:
        curry.reset(**flags)
      self.assertIsInstance(caught.exception, ValueError)
      self.assertIsInstance(caught.exception, curry.CurryError)

  def test_missing_modules_at_build(self):
    with self.assertRaises(curry.ModuleLookupError) as caught:
      curry.import_('Nosuch')
    self.assertIsInstance(caught.exception, ModuleNotFoundError)
    with self.assertRaises(curry.ModuleLookupError):
      curry.parse('1', imports=['Nosuch'])
    with self.assertRaises(curry.CompileError):
      curry.parse('Nosuch.f')

  def test_error_tree(self):
    for error in (curry.CompileError, curry.EvaluationError, curry.CurryTypeError,
        curry.ModuleLookupError, curry.IntOverflowError, curry.NoValueError, curry.StaleError):
      self.assertTrue(issubclass(error, curry.CurryError))
      self.assertTrue(issubclass(error, Exception))
    for error, standard in [(curry.DivisionByZeroError, ZeroDivisionError),
        (curry.IntOverflowError, OverflowError), (curry.ModuleLookupError, ImportError),
        (curry.NoValueError, LookupError), (curry.CurryTypeError, TypeError)]:
      self.assertTrue(issubclass(error, standard))


if __name__ == '__main__':
  unittest.main()
