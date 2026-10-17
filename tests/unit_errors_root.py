'''
The root of the error tree (the first slice of proposal A20 of the API
review): every exception class of curry.exceptions derives from CurryError,
and CurryError derives from Exception.  The three classes that derived from
BaseException (CompileError, EvaluationError and, through it,
EvaluationSuspended, and InstantiationError) become ordinary exceptions, so
that `except Exception` in a Python program sees them.  Every class keeps its
other bases (ValueError, IndexError, TypeError, ...), so `except TypeError`
still catches a CurryTypeError.  Both backends raise the same classes.

These tests are the acceptance tests of a task; they are frozen.  A change to
this file is a finding, not a fix.
'''
import cytest # from ./lib; must be first
import curry, inspect, unittest
from curry import exceptions as E

def exception_classes():
  '''Every class defined in curry.exceptions.'''
  return [
      cls for _, cls in inspect.getmembers(E, inspect.isclass)
      if cls.__module__ == E.__name__ and issubclass(cls, BaseException)
      and not issubclass(cls, Warning)
    ]

class TestErrorsRoot(unittest.TestCase):
  def test_root_is_an_exception(self):
    self.assertTrue(issubclass(E.CurryError, Exception))
    self.assertFalse(issubclass(E.CurryError, (KeyboardInterrupt, SystemExit, GeneratorExit)))
    self.assertIs(getattr(curry, 'CurryError'), E.CurryError)

  def test_every_class_derives_from_the_root(self):
    classes = exception_classes()
    self.assertGreater(len(classes), 10)
    for cls in classes:
      with self.subTest(cls=cls.__name__):
        self.assertTrue(issubclass(cls, E.CurryError))
        self.assertTrue(issubclass(cls, Exception))
        self.assertFalse(issubclass(cls, (KeyboardInterrupt, SystemExit)))

  def test_other_bases_are_kept(self):
    self.assertTrue(issubclass(E.CurryTypeError, TypeError))
    self.assertTrue(issubclass(E.CurryIndexError, IndexError))
    self.assertTrue(issubclass(E.ModuleLookupError, ModuleNotFoundError))
    self.assertTrue(issubclass(E.SymbolLookupError, AttributeError))
    self.assertTrue(issubclass(E.EvaluationSuspended, E.EvaluationError))

  def test_evaluation_error_is_caught_by_except_exception(self):
    P = curry.import_('Prelude')
    try:
      list(curry.eval((P.error)('boom')))
    except Exception as e:
      self.assertIsInstance(e, E.EvaluationError)
      self.assertIsInstance(e, E.CurryError)
      self.assertIn('boom', str(e))
    else: # pragma: no cover
      self.fail('no exception was raised')

  def test_suspension_is_a_curry_error(self):
    P = curry.import_('Prelude')
    x = curry.free('x')
    goal = (getattr(P, '=:='))((getattr(P, '+'))(x, 1), 3)
    with self.assertRaises(E.CurryError) as cm:
      list(curry.eval(goal))
    self.assertIsInstance(cm.exception, E.EvaluationSuspended)

  def test_compile_error_is_a_curry_error(self):
    with self.assertRaises(Exception) as cm:
      curry.compile('x :: Int\nx = = 1\n', mode='module')
    self.assertIsInstance(cm.exception, E.CompileError)
    self.assertIsInstance(cm.exception, E.CurryError)
