'''Tests for the pure-Python Curry interpreter.'''
import cytest # from ./lib; must be first
from curry.icurry import *
from curry import importer
from curry import interpreter
from curry.interpreter import Interpreter
from curry.interpreter import runtime
from curry.interpreter.prelude import  Prelude
from curry.visitation import dispatch
from cytest import bootstrap
from glob import glob
import curry
import os
import shutil
import unittest

from curry.interpreter import ModuleLookupError, SymbolLookupError, TypeLookupError

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
    imported = interp.import_(icur)
    self.assertEqual(set(interp.modules.keys()), set(['example', 'Prelude']))
    self.assertEqual(len(imported), 1)
    example = imported[0]
    self.assertFalse(set('A B f g main'.split()) - set(dir(example)))
    self.assertIs(interp.modules['example'], example)

    # Symbol lookup.
    self.assertIs(interp.symbol('Prelude.Int'), interp.modules['Prelude'].Int)
    self.assertRaisesRegexp(
        ModuleLookupError, r'module "blah" not found'
      , lambda: interp.symbol('blah.x')
      )
    self.assertRaisesRegexp(
        SymbolLookupError, r'module "Prelude" has no symbol "foo"'
      , lambda: interp.symbol('Prelude.foo')
      )

    # Type lookup.
    self.assertEqual(interp.type('Prelude.Int'), [interp.symbol('Prelude.Int')])
    self.assertRaisesRegexp(
        ModuleLookupError, r'module "blah" not found'
      , lambda: interp.type('blah.x')
      )
    self.assertRaisesRegexp(
        TypeLookupError, r'module "Prelude" has no type "foo"'
      , lambda: interp.type('Prelude.foo')
      )

  def testImportFile(self):
    interp = Interpreter()
    interp.path = []
    self.assertRaises(Exception, lambda: interp.import_('helloInt'))
    #
    interp.path = ['data/curry']
    self.assertMayRaise(None, lambda: interp.import_('helloInt'))
    self.assertMayRaise(None, lambda: interp.import_('helloFloat'))
    self.assertMayRaise(None, lambda: interp.import_('helloChar'))

  def testImportTimeStamp(self):
    def myeval(tempd, srcfile):
      '''Copy srcfile to tempd and evaluate it in a fresh interpreter.'''
      interp = Interpreter()
      interp.path = [tempd]
      tgtfile = os.path.join(tempd, 'test.curry')
      if srcfile is None:
        os.remove(tgtfile)
      else:
        shutil.copy(srcfile, tgtfile)
      module = interp.import_('test')
      value = next(interp.eval(interp.expr(module.main), converter='topython'))
      mtime = os.path.getmtime(importer.jsonFilename(tgtfile))
      return value, mtime

    with importer.TemporaryDirectory() as tempd:
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
    # Run interp.eval with a literal inputs (not Node).
    self.assertEqual(list(interp.eval(1)), [interp.expr(1)])

    # Evaluate an expressionw ith a leading FWD node.  It should be removed.
    P = interp.import_(Prelude)
    W = P._Fwd
    self.assertEqual(list(interp.eval([W, 1])), [interp.expr(1)])


  def testEvalValues(self):
    '''Evaluate constructor goals.'''
    interp_debug = Interpreter(flags={'debug':True})
    self.checkEvalValues(interp_debug)
    #
    interp_nodebug = Interpreter(flags={'debug':False})
    self.checkEvalValues(interp_nodebug)


  def checkEvalValues(self, interp):
    L = interp.import_(self.MYLIST)
    X = interp.import_(self.X)
    P = interp.import_(Prelude)
    bs = interp.import_(self.BOOTSTRAP)
    N,M,U,B,Z,ZN,ZF,ZQ,ZW = bs.N, bs.M, bs.U, bs.B, bs.Z, bs.ZN, bs.ZF, bs.ZQ, bs.ZW
    TESTS = [
        [[1], ['1']]
      , [[2.0], ['2.0']]
      , [[L.Cons, 0, [L.Cons, 1, L.Nil]], ['[0, 1]']]
      , [[P._Choice, 1, 2], ['1', '2']]
      , [[X.X, [P._Choice, 1, 2]], ['X 1', 'X 2']]
      , [[X.X, [P._Choice, 1, [X.X, [P._Choice, 2, [P._Choice, 3, 4]]]]], ['X 1', 'X (X 2)', 'X (X 3)', 'X (X 4)']]
      , [[P._Failure], []]
      , [[P._Choice, P._Failure, 0], ['0']]
      , [[Z, ZQ], ['N', 'M']]
      , [[Z, ZW], ['N']]
      ]
    for expr, expected in TESTS:
      goal = interp.expr(*expr)
      result = map(str, interp.eval(goal))
      self.assertEqual(set(result), set(expected))

  def testEvaluateBuiltins(self):
    interp_debug = Interpreter(flags={'debug':True})
    self.checkEvaluateBuiltins(interp_debug)
    #
    interp_nodebug = Interpreter(flags={'debug':False})
    self.checkEvaluateBuiltins(interp_nodebug)

  def checkEvaluateBuiltins(self, interp):
    P = interp.import_(Prelude)
    TESTS = [
        [[P.negate, 1], ['-1']]
      ]
    for expr, expected in TESTS:
      goal = interp.expr(expr)
      result = map(str, interp.eval(goal))
      self.assertEqual(set(result), set(expected))

