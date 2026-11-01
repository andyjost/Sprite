import cytest # from ./lib; must be first
import curry
from curry import config, inspect, icurry
from curry.toolchain._mergecurry import validatemodule
from curry.backends.cxx import curryrtbindings as curryrt
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
    with self.assertLogs('curry.toolchain._mergecurry', level='INFO') as logs:
      validatemodule(module)
      validatemodule(icurry.IModule('MissingPrimitive', imports=[], types=[],
          functions=[icurry.IFunction('MissingPrimitive.f', 0,
              body=icurry.IExternal('MissingPrimitive.f'))]))
    self.assertEqual(logs.output, [
        'INFO:curry.toolchain._mergecurry:module MissingPrimitive: '
        '1 externals without a primitive raise when called'])
    self.assertTrue(module.functions['f'].is_external)

  @cytest.with_flags(interpret='off')
  def test_library(self):
    self.check_library()
    IO = curry.import_('System.IO')
    self.assertFalse(curryrt.icurry_is_interpreted(IO.stdin.info))

  @cytest.with_flags(interpret='off')
  def test_compiled_external_type(self):
    M = curry.compile("""
        external data T
        f :: T -> Int
        f external
        g = 1
        x :: T
        x = error "argument evaluated"
        apply h x = h x
        """)
    self.assertEqual(curry.info(M).types['T'].constructors, ())
    self.assertFalse(curryrt.icurry_is_interpreted(M.f.info))
    self.assertEqual(curry.eval(M.g).one(), 1)
    for expr in [M.f(M.x), M.apply(M.f, M.x)]:
      with self.assertRaisesRegex(EvaluationError,
          M.f.fullname + r': not implemented \(no primitive in the runtime\)'):
        list(curry.eval(expr))

  @cytest.with_flags(interpret='all')
  def test_interpreted_library(self):
    self.check_library()
