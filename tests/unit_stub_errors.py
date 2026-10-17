'''
Errors: frozen acceptance of Appendix A of python-api-review2.md.

Each row maps a test to the review's lines and the flip lane of
python-api-implementation-plan.md. Section 12 amends metadata access.
  test_CurryError_bases: lines 6435; lane 1.
  test_CurryTypeError_bases: lines 6438; lane 1.
  test_ConversionError_bases: lines 6449; lane 1.
  test_MismatchError_bases: lines 6452; lane 1.
  test_ArityError_bases: lines 6455; lane 1.
  test_NoInstanceError_bases: lines 6458; lane 1.
  test_DefaultingError_bases: lines 6461; lane 1.
  test_TypeSyntaxError_bases: lines 6473; lane 1.
  test_InterfaceError_bases: lines 6476; lane 1.
  test_IntOverflowError_bases: lines 6479; lane 1.
  test_CompileError_bases: lines 6488; lane 1.
  test_EvaluationError_bases: lines 6498; lane 1.
  test_SuspensionError_bases: lines 6505; lane 1.
  test_DivisionByZeroError_bases: lines 6512; lane 1.
  test_CurryIOError_bases: lines 6515; lane 1.
  test_CurryFileNotFoundError_bases: lines 6518; lane 1.
  test_NondetError_bases: lines 6521; lane 1.
  test_StackLimitError_bases: lines 6524; lane 1.
  test_EvaluationTimeout_bases: lines 6527; lane 1.
  test_InstantiationError_bases: lines 6530; lane 1.
  test_NoValueError_bases: lines 6533; lane 1.
  test_ManyValuesError_bases: lines 6536; lane 1.
  test_ModuleLookupError_bases: lines 6539; lane 1.
  test_ModuleExistsError_bases: lines 6542; lane 1.
  test_SymbolLookupError_bases: lines 6545; lane 1.
  test_TypeLookupError_bases: lines 6548; lane 1.
  test_StaleError_bases: lines 6551; lane 1.
  test_LoadError_bases: lines 6559; lane 1.
  test_PrerequisiteError_bases: lines 6562; lane 1.
  test_FlagError_bases: lines 6565; lane 1.
  test_NotConstructorError_bases: lines 6568; lane 1.
  test_CurryIndexError_bases: lines 6571; lane 1.
  test_CurryWarning_bases: lines 6574; lane 1.
  test_conversion_message_example: lines 6445-6446; lane 1.
  test_defaulting_message_example: lines 6467-6470; lane 1.
  test_int_overflow_message_example: lines 6484-6485; lane 1.
  test_arity_message: lines 6455-6456; lane 1.
  test_no_instance_message: lines 6458-6459; lane 1.
  test_type_syntax_rejects_invalid_annotation: lines 6473-6474; lane 1.
  test_type_syntax_rejects_unknown_type: lines 6473-6474; lane 1.
  test_type_syntax_rejects_wrong_kind: lines 6473-6474; lane 1.
  test_int_overflow_during_step_has_same_class: lines 6481-6482; lane 1.
  test_compile_error_has_report_and_position: lines 6488-6496; lane 1.
  test_evaluation_error_message: lines 6498-6503; lane 1.
  test_user_io_error_message: lines 6500-6502; lane 1.
  test_suspension_message_after_other_values: lines 6505-6509; lane 1.
  test_division_by_zero_message: lines 6512-6513; lane 1.
  test_float_division_keeps_ieee_result: lines 6513; lane 1.
  test_file_not_found_sets_filename: lines 6518-6519; lane 1.
  test_nondeterminism_in_io_is_nondet_error: lines 6521-6522; lane 1.
  test_no_value_message: lines 6533-6534; lane 1.
  test_many_values_message: lines 6536-6537; lane 1.
  test_missing_module_is_import_error: lines 6539-6540; lane 1.
  test_missing_module_hook_is_import_error: lines 6539-6540; lane 1.
  test_module_exists_message: lines 6542-6543; lane 1.
  test_missing_symbol_message: lines 6545-6546; lane 1.
  test_type_name_message_uses_info: lines 6545-6546; 6667-6677; lane 1.
  test_missing_type_raises_type_lookup_error: lines 6548-6549; 6667-6677; lane 1.
  test_stale_message_names_module_event_and_rebuild: lines 6551-6556; lane 1.
  test_load_message_names_file_and_backend: lines 6559-6560; lane 1.
  test_flag_error_message: lines 6565-6566; lane 1.
  test_warning_can_be_filtered: lines 6574-6575; lane 1.
  test_logger_has_null_handler: lines 6430-6432; lane 1.
  test_mismatch_error_shows_parameter_and_argument_types: lines 6452-6453; lane 1.
  test_free_function_cannot_be_instantiated: lines 6530-6531; lane 1.
  test_import_does_not_configure_root_logger: lines 6431-6432; lane 1.
  test_frontend_warning_uses_curry_warning: lines 6430-6431; 6574-6575; lane 1.
  test_int_boundary_is_signed_64_bits: lines 5740-5741; 6481-6482; lane 1.

Examples left out: none. Setup prompts have their own tests; result
tests repeat their setup so they can run independently.
'''
import cytest # from ./lib; must be first
import curry
import unittest
import os
import logging
import subprocess
import sys
import tempfile
import warnings
from unittest import mock

FLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'curry', 'flows')


def setUpModule():
  curry.path.insert(0, FLOW_PATH)


class TestStubErrors(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  def test_CurryError_bases(self):
    self.assertEqual(curry.CurryError.__bases__, (Exception,))
    self.assertTrue(issubclass(curry.CurryError, Exception))

  def test_CurryTypeError_bases(self):
    self.assertEqual(curry.CurryTypeError.__bases__, (curry.CurryError, TypeError))
    self.assertTrue(issubclass(curry.CurryTypeError, Exception))

  @unittest.expectedFailure
  def test_ConversionError_bases(self):
    self.assertEqual(curry.ConversionError.__bases__, (curry.CurryTypeError,))
    self.assertTrue(issubclass(curry.ConversionError, Exception))

  @unittest.expectedFailure
  def test_MismatchError_bases(self):
    self.assertEqual(curry.MismatchError.__bases__, (curry.CurryTypeError,))
    self.assertTrue(issubclass(curry.MismatchError, Exception))

  @unittest.expectedFailure
  def test_ArityError_bases(self):
    self.assertEqual(curry.ArityError.__bases__, (curry.CurryTypeError,))
    self.assertTrue(issubclass(curry.ArityError, Exception))

  @unittest.expectedFailure
  def test_NoInstanceError_bases(self):
    self.assertEqual(curry.NoInstanceError.__bases__, (curry.CurryTypeError,))
    self.assertTrue(issubclass(curry.NoInstanceError, Exception))

  def test_DefaultingError_bases(self):
    self.assertEqual(curry.DefaultingError.__bases__, (curry.CurryTypeError,))
    self.assertTrue(issubclass(curry.DefaultingError, Exception))

  @unittest.expectedFailure
  def test_TypeSyntaxError_bases(self):
    self.assertEqual(curry.TypeSyntaxError.__bases__, (curry.CurryTypeError,))
    self.assertTrue(issubclass(curry.TypeSyntaxError, Exception))

  @unittest.expectedFailure
  def test_InterfaceError_bases(self):
    self.assertEqual(curry.InterfaceError.__bases__, (curry.CurryTypeError,))
    self.assertTrue(issubclass(curry.InterfaceError, Exception))

  @unittest.expectedFailure
  def test_IntOverflowError_bases(self):
    self.assertEqual(curry.IntOverflowError.__bases__, (curry.CurryError, OverflowError))
    self.assertTrue(issubclass(curry.IntOverflowError, Exception))

  def test_CompileError_bases(self):
    self.assertEqual(curry.CompileError.__bases__, (curry.CurryError,))
    self.assertTrue(issubclass(curry.CompileError, Exception))

  def test_EvaluationError_bases(self):
    self.assertEqual(curry.EvaluationError.__bases__, (curry.CurryError,))
    self.assertTrue(issubclass(curry.EvaluationError, Exception))

  @unittest.expectedFailure
  def test_SuspensionError_bases(self):
    self.assertEqual(curry.SuspensionError.__bases__, (curry.EvaluationError,))
    self.assertTrue(issubclass(curry.SuspensionError, Exception))

  @unittest.expectedFailure
  def test_DivisionByZeroError_bases(self):
    self.assertEqual(curry.DivisionByZeroError.__bases__, (curry.EvaluationError, ZeroDivisionError))
    self.assertTrue(issubclass(curry.DivisionByZeroError, Exception))

  @unittest.expectedFailure
  def test_CurryIOError_bases(self):
    self.assertEqual(curry.CurryIOError.__bases__, (curry.EvaluationError, OSError))
    self.assertTrue(issubclass(curry.CurryIOError, Exception))

  @unittest.expectedFailure
  def test_CurryFileNotFoundError_bases(self):
    self.assertEqual(curry.CurryFileNotFoundError.__bases__, (curry.CurryIOError, FileNotFoundError))
    self.assertTrue(issubclass(curry.CurryFileNotFoundError, Exception))

  @unittest.expectedFailure
  def test_NondetError_bases(self):
    self.assertEqual(curry.NondetError.__bases__, (curry.EvaluationError,))
    self.assertTrue(issubclass(curry.NondetError, Exception))

  @unittest.expectedFailure
  def test_StackLimitError_bases(self):
    self.assertEqual(curry.StackLimitError.__bases__, (curry.EvaluationError, RecursionError))
    self.assertTrue(issubclass(curry.StackLimitError, Exception))

  @unittest.expectedFailure
  def test_EvaluationTimeout_bases(self):
    self.assertEqual(curry.EvaluationTimeout.__bases__, (curry.EvaluationError,))
    self.assertTrue(issubclass(curry.EvaluationTimeout, Exception))

  @unittest.expectedFailure
  def test_InstantiationError_bases(self):
    self.assertEqual(curry.InstantiationError.__bases__, (curry.EvaluationError,))
    self.assertTrue(issubclass(curry.InstantiationError, Exception))

  @unittest.expectedFailure
  def test_NoValueError_bases(self):
    self.assertEqual(curry.NoValueError.__bases__, (curry.CurryError, LookupError))
    self.assertTrue(issubclass(curry.NoValueError, Exception))

  @unittest.expectedFailure
  def test_ManyValuesError_bases(self):
    self.assertEqual(curry.ManyValuesError.__bases__, (curry.CurryError, ValueError))
    self.assertTrue(issubclass(curry.ManyValuesError, Exception))

  @unittest.expectedFailure
  def test_ModuleLookupError_bases(self):
    self.assertEqual(curry.ModuleLookupError.__bases__, (curry.CurryError, ModuleNotFoundError))
    self.assertTrue(issubclass(curry.ModuleLookupError, Exception))

  @unittest.expectedFailure
  def test_ModuleExistsError_bases(self):
    self.assertEqual(curry.ModuleExistsError.__bases__, (curry.CurryError, ValueError))
    self.assertTrue(issubclass(curry.ModuleExistsError, Exception))

  def test_SymbolLookupError_bases(self):
    self.assertEqual(curry.SymbolLookupError.__bases__, (curry.CurryError, AttributeError))
    self.assertTrue(issubclass(curry.SymbolLookupError, Exception))

  def test_TypeLookupError_bases(self):
    self.assertEqual(curry.TypeLookupError.__bases__, (curry.CurryError, AttributeError))
    self.assertTrue(issubclass(curry.TypeLookupError, Exception))

  @unittest.expectedFailure
  def test_StaleError_bases(self):
    self.assertEqual(curry.StaleError.__bases__, (curry.CurryError, RuntimeError))
    self.assertTrue(issubclass(curry.StaleError, Exception))

  @unittest.expectedFailure
  def test_LoadError_bases(self):
    self.assertEqual(curry.LoadError.__bases__, (curry.CurryError, OSError))
    self.assertTrue(issubclass(curry.LoadError, Exception))

  def test_PrerequisiteError_bases(self):
    self.assertEqual(curry.PrerequisiteError.__bases__, (curry.CurryError, OSError))
    self.assertTrue(issubclass(curry.PrerequisiteError, Exception))

  @unittest.expectedFailure
  def test_FlagError_bases(self):
    self.assertEqual(curry.FlagError.__bases__, (curry.CurryError, ValueError))
    self.assertTrue(issubclass(curry.FlagError, Exception))

  def test_NotConstructorError_bases(self):
    self.assertEqual(curry.NotConstructorError.__bases__, (curry.CurryError, ValueError))
    self.assertTrue(issubclass(curry.NotConstructorError, Exception))

  def test_CurryIndexError_bases(self):
    self.assertEqual(curry.CurryIndexError.__bases__, (curry.CurryError, IndexError))
    self.assertTrue(issubclass(curry.CurryIndexError, Exception))

  @unittest.expectedFailure
  def test_CurryWarning_bases(self):
    self.assertEqual(curry.CurryWarning.__bases__, (UserWarning,))
    self.assertTrue(issubclass(curry.CurryWarning, Exception))

  @unittest.expectedFailure
  def test_conversion_message_example(self):
    P = curry.import_('Prelude')
    with self.assertRaises(curry.ConversionError) as caught:
      P.ord('a')
    self.assertEqual(
        str(caught.exception)
      , "cannot convert 'a' to Char at argument 1 of Prelude.ord :: Char -> Int: a str is a String; write curry.Char('a')"
      )

  @unittest.expectedFailure
  def test_defaulting_message_example(self):
    P = curry.import_('Prelude')
    with self.assertRaises(curry.DefaultingError) as caught:
      curry.eval(P.read('5'))
    self.assertEqual(
        str(caught.exception)
      , 'cannot handle the overloaded goal read "5" of type Read a => a\nCannot handle arbitrary overloaded top-level expressions\nstate the type: curry.term(P.read(\'5\'), type=\'Int\')'
      )

  @unittest.expectedFailure
  def test_int_overflow_message_example(self):
    with self.assertRaises(curry.IntOverflowError) as caught:
      curry.term(2 ** 63)
    self.assertEqual(
        str(caught.exception)
      , '9223372036854775808 is outside the range of Int (-9223372036854775808 to 9223372036854775807)'
      )

  def test_arity_message(self):
    Items = curry.import_('Items')
    with self.assertRaises(curry.ArityError) as caught:
      Items.A(1)
    self.assertEqual(str(caught.exception), 'Items.A :: Item takes 0 arguments, 1 given')

  @unittest.expectedFailure
  def test_no_instance_message(self):
    P = curry.import_('Prelude')
    with self.assertRaises(curry.NoInstanceError) as caught:
      P['+'](True, True)
    self.assertEqual(str(caught.exception), 'no instance for Num Bool in argument 1 of Prelude.+')

  @unittest.expectedFailure
  def test_type_syntax_rejects_invalid_annotation(self):
    with self.assertRaises(curry.TypeSyntaxError):
      curry.term(1, type='[')

  @unittest.expectedFailure
  def test_type_syntax_rejects_unknown_type(self):
    with self.assertRaises(curry.TypeSyntaxError):
      curry.term(1, type='NoSuchType')

  @unittest.expectedFailure
  def test_type_syntax_rejects_wrong_kind(self):
    with self.assertRaises(curry.TypeSyntaxError):
      curry.term([], type='Maybe')

  @unittest.expectedFailure
  def test_int_overflow_during_step_has_same_class(self):
    P = curry.import_('Prelude')
    r = curry.eval(P['+'](curry.term(2 ** 63 - 1, type='Int'), 1))
    with self.assertRaises(curry.IntOverflowError):
      next(r)

  def test_compile_error_has_report_and_position(self):
    with self.assertRaises(curry.CompileError) as caught:
      curry.parse('1 + )')
    error = caught.exception
    self.assertIsInstance(error.report, str)
    self.assertTrue(error.report)
    self.assertEqual((error.line, error.column), (1, 5))
    self.assertNotIn(tempfile.gettempdir(), str(error))

  def test_evaluation_error_message(self):
    P = curry.import_('Prelude')
    r = curry.eval(P.error('boom'))
    with self.assertRaises(curry.EvaluationError) as caught:
      next(r)
    self.assertEqual(str(caught.exception), 'boom')

  def test_user_io_error_message(self):
    P = curry.import_('Prelude')
    with self.assertRaises(curry.EvaluationError) as caught:
      next(curry.eval(P.ioError(P.userError('x'))))
    self.assertEqual(str(caught.exception), 'user error: x')

  @unittest.expectedFailure
  def test_suspension_message_after_other_values(self):
    M = curry.import_('Tools')
    goal = curry.choice(True, M.suspend)
    r = curry.eval(goal)
    self.assertIs(next(r), True)
    with self.assertRaises(curry.SuspensionError) as caught:
      next(r)
    self.assertEqual(str(caught.exception), 'Evaluation suspended: ' + str(goal))

  @unittest.expectedFailure
  def test_division_by_zero_message(self):
    P = curry.import_('Prelude')
    with self.assertRaises(curry.DivisionByZeroError) as caught:
      next(curry.eval(P.div(1, 0)))
    self.assertIsInstance(caught.exception, ZeroDivisionError)
    self.assertEqual(str(caught.exception), 'division by zero: div 1 0')

  @unittest.expectedFailure
  def test_float_division_keeps_ieee_result(self):
    P = curry.import_('Prelude')
    self.assertEqual(curry.eval(P['/'](1.0, 0.0)).one(), float('inf'))

  @unittest.expectedFailure
  def test_file_not_found_sets_filename(self):
    P = curry.import_('Prelude')
    with self.assertRaises(curry.CurryFileNotFoundError) as caught:
      next(curry.eval(P.readFile('/nosuch')))
    self.assertIsInstance(caught.exception, FileNotFoundError)
    self.assertEqual(caught.exception.filename, '/nosuch')

  @unittest.expectedFailure
  def test_nondeterminism_in_io_is_nondet_error(self):
    P = curry.import_('Prelude')
    with self.assertRaises(curry.NondetError):
      next(curry.eval(P.print(curry.choice(1, 2))))

  @unittest.expectedFailure
  def test_no_value_message(self):
    Stream = curry.import_('Stream')
    with self.assertRaises(curry.NoValueError) as caught:
      curry.eval(Stream.nothing).one()
    self.assertEqual(str(caught.exception), 'No value found: nothing')

  @unittest.expectedFailure
  def test_many_values_message(self):
    Coin = curry.import_('Coin')
    with self.assertRaises(curry.ManyValuesError) as caught:
      curry.eval(Coin.coin).one()
    self.assertEqual(str(caught.exception), 'more than one value: coin has 0 and 1')

  @unittest.expectedFailure
  def test_missing_module_is_import_error(self):
    with self.assertRaises(curry.ModuleLookupError) as caught:
      curry.import_('StubMissingModule')
    self.assertIsInstance(caught.exception, ImportError)

  @unittest.expectedFailure
  def test_missing_module_hook_is_import_error(self):
    with self.assertRaises(curry.ModuleLookupError) as caught:
      from curry.lib import StubMissingModule
    self.assertIsInstance(caught.exception, ImportError)

  @unittest.expectedFailure
  def test_module_exists_message(self):
    curry.compile('f :: Int\nf = 1', name='Same')
    with self.assertRaises(curry.ModuleExistsError) as caught:
      curry.compile('f :: Int\nf = 2', name='Same')
    self.assertEqual(
        str(caught.exception)
      , "module 'Same' is loaded; curry.reload(curry.modules['Same'], text=...) replaces its code"
      )

  def test_missing_symbol_message(self):
    Tools = curry.import_('Tools')
    with self.assertRaises(curry.SymbolLookupError) as caught:
      Tools.nosuch
    self.assertEqual(str(caught.exception), "module 'Tools' has no symbol 'nosuch'")

  def test_type_name_message_uses_info(self):
    Items = curry.import_('Items')
    with self.assertRaises(curry.SymbolLookupError) as caught:
      Items.Item
    self.assertEqual(str(caught.exception), "'Item' is a type: curry.info(Items).types['Item']")

  @unittest.expectedFailure
  def test_missing_type_raises_type_lookup_error(self):
    M = curry.import_('Items')
    with self.assertRaises(curry.TypeLookupError):
      curry.type('Items.NoSuchType')
    with self.assertRaises(curry.TypeLookupError):
      curry.info(M).types['NoSuchType']

  @unittest.expectedFailure
  def test_stale_message_names_module_event_and_rebuild(self):
    Coin = curry.import_('Coin')
    old = Coin.inc(1)
    curry.reset()
    with self.assertRaises(curry.StaleError) as caught:
      curry.eval(old).one()
    text = str(caught.exception)
    self.assertIn('Coin', text)
    self.assertIn('reset', text)
    self.assertIn('build it again from Coin', text)

  @unittest.expectedFailure
  def test_load_message_names_file_and_backend(self):
    with self.assertRaises(curry.LoadError) as caught:
      curry.load('stub-missing.so')
    text = str(caught.exception)
    self.assertIn('stub-missing.so', text)
    self.assertIn(curry.flags['backend'], text)

  @unittest.expectedFailure
  def test_flag_error_message(self):
    with self.assertRaises(curry.FlagError) as caught:
      curry.reset(bogus=True)
    text = str(caught.exception)
    self.assertTrue(text.startswith("'bogus' is not a flag; the flags are "))
    for name in ('backend', 'interpret', 'rotation', 'stack_limit'):
      self.assertIn(name, text)

  @unittest.expectedFailure
  def test_warning_can_be_filtered(self):
    with warnings.catch_warnings(record=True) as seen:
      warnings.simplefilter('ignore', curry.CurryWarning)
      warnings.warn('stub warning', curry.CurryWarning)
    self.assertEqual(seen, [])
    with self.assertWarns(curry.CurryWarning):
      warnings.warn('stub warning', curry.CurryWarning)

  @unittest.expectedFailure
  def test_logger_has_null_handler(self):
    self.assertTrue(any(isinstance(h, logging.NullHandler) for h in logging.getLogger('curry').handlers))

  @unittest.expectedFailure
  def test_mismatch_error_shows_parameter_and_argument_types(self):
    Coin = curry.import_('Coin')
    with self.assertRaises(curry.MismatchError) as caught:
      Coin.inc(curry.term(True))
    self.assertIn('Bool', str(caught.exception))
    self.assertIn('Int', str(caught.exception))

  @unittest.expectedFailure
  def test_free_function_cannot_be_instantiated(self):
    f = curry.free('f', type='Int -> Int')
    with self.assertRaises(curry.InstantiationError):
      next(curry.eval(f(1)))

  @unittest.expectedFailure
  def test_import_does_not_configure_root_logger(self):
    code = "import logging; before = tuple(logging.getLogger().handlers); import curry; assert tuple(logging.getLogger().handlers) == before"
    run = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    self.assertEqual(run.returncode, 0, run.stderr)

  @unittest.expectedFailure
  def test_frontend_warning_uses_curry_warning(self):
    with mock.patch.dict(os.environ, {'SPRITE_FRONTEND_WARNINGS': '1'}):
      with self.assertWarns(curry.CurryWarning):
        curry.compile('f :: Int -> Int\nf 0 = 1\nf x = 2')

  @unittest.expectedFailure
  def test_int_boundary_is_signed_64_bits(self):
    for value in (-2 ** 63, 2 ** 63 - 1):
      self.assertEqual(curry.eval(curry.term(value)).one(), value)
    with self.assertRaises(curry.IntOverflowError):
      curry.term(-2 ** 63 - 1)


if __name__ == '__main__':
  unittest.main()
