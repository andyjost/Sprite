'''Tests for the pure-Python Curry interpreter.'''
from curry.icurry import *
from curry.interpreter import Interpreter, Prelude, SymbolLookupError, System
from curry.interpreter import runtime
from curry.visitation import dispatch
from cytest import bootstrap
from glob import glob
import cytest # from ./lib
import unittest

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
    self.assertEqual(set(interp.modules.keys()), set(['example', 'Prelude', '_System']))
    self.assertEqual(len(imported), 1)
    example = imported[0]
    self.assertFalse(set('A B f f_case_#1 g main'.split()) - set(dir(example)))
    self.assertIs(interp.modules['example'], example)

    # Symbol lookup.
    self.assertIs(interp.symbol('Prelude.Int'), interp.modules['Prelude'].Int)
    self.assertRaisesRegexp(
        SymbolLookupError, r'module "blah" not found'
      , lambda: interp.symbol('blah.x')
      )
    self.assertRaisesRegexp(
        SymbolLookupError, r'module "Prelude" has no symbol "foo"'
      , lambda: interp.symbol('Prelude.foo')
      )

    # Type lookup.
    self.assertEqual(interp.type('Prelude.Int'), [interp.symbol('Prelude.Int')])
    self.assertRaisesRegexp(
        SymbolLookupError, r'module "blah" not found'
      , lambda: interp.type('blah.x')
      )
    self.assertRaisesRegexp(
        SymbolLookupError, r'module "Prelude" has no type "foo"'
      , lambda: interp.type('Prelude.foo')
      )

  def testImportFile(self):
    interp = Interpreter()
    interp.path = ['data/curry']
    self.assertMayRaise(None, lambda: interp.import_('helloInt'))
    self.assertMayRaise(None, lambda: interp.import_('helloFloat'))
    self.assertMayRaise(None, lambda: interp.import_('helloChar'))

  def testCoverage(self):
    '''Tests to get complete line coverage.'''
    interp = Interpreter()
    # Run interp.eval with a literal inputs (not Node).
    self.assertEqual(list(interp.eval(1)), [interp.expr(1)])

    # Evaluate an expressionw ith a leading FWD node.  It should be removed.
    P = interp.import_(Prelude)
    S = interp.import_(System)
    W = S.Fwd
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
    S = interp.import_(System)
    bs = interp.import_(self.BOOTSTRAP)
    N,M,U,B,Z,ZN,ZF,ZQ,ZW = bs.N, bs.M, bs.U, bs.B, bs.Z, bs.ZN, bs.ZF, bs.ZQ, bs.ZW
    TESTS = [
        [[1], ['1']]
      , [[2.0], ['2.0']]
      , [[L.Cons, 0, [L.Cons, 1, L.Nil]], ['[0, 1]']]
      , [[S.Choice, 1, 2], ['1', '2']]
      , [[X.X, [S.Choice, 1, 2]], ['X 1', 'X 2']]
      , [[X.X, [S.Choice, 1, [X.X, [S.Choice, 2, [S.Choice, 3, 4]]]]], ['X 1', 'X (X 2)', 'X (X 3)', 'X (X 4)']]
      , [[S.Failure], []]
      , [[S.Choice, S.Failure, 0], ['0']]
      , [[Z, ZQ], ['N', 'M']]
      , [[Z, ZW], ['N']]
      ]
    for expr, expected in TESTS:
      goal = interp.expr(expr)
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

