import cytest # from ./lib; must be first
import curry
from curry import config, inspect, icurry
from curry.toolchain._mergecurry import validatemodule
from unittest import mock
from curry.exceptions import EvaluationError

OLD_UNSUPPORTED = (
    'Control.Search.SearchTree', 'Curry.Compiler.Distribution', 'Data.IORef',
    'Debug.Trace', 'System.CPUTime', 'System.Environment', 'System.IO',
    'System.IO.Unsafe', 'Test.Prop', 'Test.Prop.Types')

class TestLibraryExternals(cytest.TestCase):
  def check_library(self):
    self.assertTrue(set(OLD_UNSUPPORTED) <= set(config.syslibs()))
    for name in config.syslibs():
      with self.subTest(module=name):
        self.assertIsNotNone(curry.import_(name))
    D = curry.import_('Curry.Compiler.Distribution')
    with self.assertRaisesRegex(EvaluationError,
        r'Curry.Compiler.Distribution.curryCompiler: not implemented'):
      list(curry.eval(D.curryCompiler))
    implementation = inspect.getimpl(D.curryCompiler)
    self.assertIn('external', implementation)
    self.assertIn('not implemented', implementation)
    with self.assertRaisesRegex(EvaluationError, r'System.IO.*not implemented'):
      list(curry.eval(curry.parse('trace "x" (1 :: Int)', imports=['Debug.Trace'])))
    IO = curry.import_('System.IO')
    self.assertEqual(curry.info(IO).types['Handle'].constructors, ())
    self.assertEqual(curry.typeof(IO.stdin), 'Handle')
    self.assertEqual(curry.show(IO.stdin), 'stdin')
    self.assertEqual([curry.show(v) for v in curry.eval(
        curry.parse('Ok', imports=['Test.Prop.Types']))], ['Ok'])

  def test_validation_reports_once(self):
    module = icurry.IModule('MissingPrimitive', imports=[], types=[], functions=[
        icurry.IFunction('MissingPrimitive.f', 0,
            body=icurry.IExternal('MissingPrimitive.f'))])
    with mock.patch('curry.toolchain._mergecurry.logging.getLogger') as logger:
      validatemodule(module)
      validatemodule(module)
    logger.return_value.info.assert_called_once_with(
        'module %s: %d externals without a primitive raise when called',
        'MissingPrimitive', 1)
    self.assertTrue(module.functions['f'].is_external)

  def test_library(self):
    self.check_library()

  @cytest.with_flags(interpret='all')
  def test_interpreted_library(self):
    self.check_library()
