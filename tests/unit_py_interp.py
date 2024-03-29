'''Tests for the pure-Python Curry interpreter.'''
import cytest # from ./lib; must be first
from curry.exceptions import ModuleLookupError, SymbolLookupError, TypeLookupError
from curry.icurry import *
from curry import interpreter, toolchain, unboxed
from curry.interpreter import Interpreter
from curry.utility.binding import binding, del_
from curry.utility import filesys
from curry.utility.visitation import dispatch
from cytest import bootstrap
from glob import glob
import curry, os, shutil, unittest

class TestPyInterp(cytest.TestCase):
  '''Tests for the pure-Python Curry interpreter.'''
  @classmethod
  def setUpClass(cls):
    cls.BOOTSTRAP = bootstrap.getbootstrap()
    cls.EXAMPLE = bootstrap.getexample()
    cls.MYLIST = bootstrap.getlist()
    cls.X = bootstrap.getx();

  @classmethod
  def tearDownClass(cls):
    del cls.BOOTSTRAP
    del cls.EXAMPLE
    del cls.MYLIST
    del cls.X

  def testImportICurry(self):
    icur = self.EXAMPLE
    interp = Interpreter()
    example = interp.import_(icur)
    self.assertEqual(set(interp.modules.keys()), set(['example', 'Prelude']))
    self.assertFalse(set('A B f g main'.split()) - set(dir(example)))
    self.assertIs(interp.modules['example'], example)

    # Symbol lookup.
    self.assertIs(interp.symbol('Prelude.Int'), interp.modules['Prelude'].Int)
    self.assertRaisesRegex(
        ModuleLookupError, "Curry module 'blah' not found"
      , lambda: interp.symbol('blah.x')
      )
    self.assertRaisesRegex(
        SymbolLookupError, "module 'Prelude' has no symbol 'foo'"
      , lambda: interp.symbol('Prelude.foo')
      )

    # Type lookup.
    typedef = interp.type('Prelude.Int')
    self.assertEqual(typedef.constructors , (interp.symbol('Prelude.Int'),))
    self.assertEqual(typedef.fullname , 'Prelude.Int')
    self.assertEqual(typedef.name , 'Int')
    self.assertRaisesRegex(
        ModuleLookupError, "module 'blah' not found"
      , lambda: interp.type('blah.x')
      )
    self.assertRaisesRegex(
        TypeLookupError, "module 'Prelude' has no type 'foo'"
      , lambda: interp.type('Prelude.foo')
      )

  def testImportFile(self):
    # Ignore the data/curry path added by cytest.TestCase.
    with binding(os.environ, 'CURRYPATH', del_):
      interp = Interpreter()
    self.assertRaises(Exception, lambda: interp.import_('helloInt'))
    #
    interp.path.insert(0, 'data/curry')
    self.assertMayRaise(None, lambda: interp.import_('helloInt'))
    self.assertMayRaise(None, lambda: interp.import_('helloFloat'))
    self.assertMayRaise(None, lambda: interp.import_('helloChar'))

  @unittest.expectedFailure
  def testImportTimeStamp(self):
    def myeval(tempd, srcfile):
      '''Copy srcfile to tempd and evaluate it in a fresh interpreter.'''
      interp = Interpreter()
      interp.path.insert(0, tempd)
      tgtfile = os.path.join(tempd, 'test.curry')
      if srcfile is None:
        os.remove(tgtfile)
      else:
        shutil.copy(srcfile, tgtfile)
      module = interp.import_('test')
      value = next(interp.eval(interp.raw_expr(module.main), converter='topython'))
      for jsonfile in toolchain.jsonfilenames(tgtfile):
        try:
          mtime = os.path.getmtime(jsonfile)
          break
        except OSError:
          pass
      else:
        self.assertFalse('No JSON file found')
      return value, mtime

    with filesys.TemporaryDirectory() as tempd:
      # Copy the helloInt module into the temp dir and run it.
      a_value, a_mtime = myeval(tempd, 'data/curry/helloInt.curry')
      self.assertEqual(a_value, 0)

      # Repeat with helloChar, overwriting the previous source file.
      b_value, b_mtime = myeval(tempd, 'data/curry/helloChar.curry')
      self.assertEqual(b_value, 'a')

      # Check that the "b" JSON file is newer than the "a" JSON file.
      self.assertGreater(b_mtime, a_mtime)

      # Finally, remove the .curry file and ensure the module is still
      # loadable.
      c_value, c_mtime = myeval(tempd, None)
      self.assertEqual(c_value, 'a')
      self.assertEqual(b_mtime, c_mtime)

  def testCoverage(self):
    '''Tests to get complete line coverage.'''
    interp = Interpreter()
    # Run interp.eval with a literal as input (not Node).
    self.assertEqual(list(interp.eval(1)), [interp.raw_expr(1)])

    # Evaluate an expression with a leading FWD node.  It should be removed.
    # W = interp.backend.fundamental_symbols.Fwd
    # self.assertEqual(list(interp.eval([W, 1])), [interp.raw_expr(1)])


  @cytest.with_flags(defaultconverter='topython')
  def testEvalValues(self):
    '''Evaluate constructor goals.'''
    interp_debug = Interpreter(flags={'debug':True})
    self.checkEvalValues(interp_debug)
    #
    interp_nodebug = Interpreter(flags={'debug':False})
    self.checkEvalValues(interp_nodebug)


  def format_list(self, arg):
    if arg.startswith('[') and arg.endswith(']'):
      values = arg[1:-1].split(', ')
      s = 'Nil'
      for part in reversed(arg[1:-1].split(', ')):
        s = '(Cons %s %s)' % (part, s)
      return s[1:-1] if s.startswith('(') else s
    else:
      return str(arg)

  def checkEvalValues(self, interp):
    L = interp.import_(self.MYLIST)
    X = interp.import_(self.X)
    Choice = interp.backend.fundamental_symbols.Choice
    Failure = interp.backend.fundamental_symbols.Failure
    bs = interp.import_(self.BOOTSTRAP)
    cid = bootstrap.cid
    N,M,U,B,Z,ZN,ZF = bs.N, bs.M, bs.U, bs.B, bs.Z, bs.ZN, bs.ZF
    TESTS = [
        [[1], ['1']]
      , [[2.0], ['2.0']]
      , [[L.Cons, 0, [L.Cons, 1, L.Nil]], ['[0, 1]']]
      , [[Choice, cid, 1, 2], ['1', '2']]
      , [[X.X, [Choice, cid, 1, 2]], ['X 1', 'X 2']]
      , [[X.X, [Choice, unboxed(0), 1, [X.X, [Choice, unboxed(1), 2, [Choice, unboxed(2), 3, 4]]]]], ['X 1', 'X (X 2)', 'X (X 3)', 'X (X 4)']]
      , [[Failure], []]
      , [[Choice, cid, Failure, 0], ['0']]
      ]
    for expr, expected in TESTS:
      goal = interp.raw_expr(*expr)
      result = map(str, interp.eval(goal))
      expected = map(self.format_list, expected)
      self.assertEqual(set(result), set(expected))

