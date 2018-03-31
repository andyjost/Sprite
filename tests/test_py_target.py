'''Tests for Curry code targeted to Python.'''
from curry.icurry import *
from curry.interpreter import Interpreter, Prelude, SymbolLookupError, System
from curry.interpreter import runtime
from curry.visitation import dispatch
import cytest
from glob import glob
import gzip
import operator as op
import unittest

def listformat(node):
  def gen():
    p = node
    while p.info.name == 'Cons':
      value = p.successors[0]
      yield value.info.show(value)
      p = p.successors[1]
  return '[' + ', '.join(gen()) + ']'

def getbootstrap():
  return IModule(
      name='bootstrap'
    , imports=['_System']
    , types=[
          IType(
              ident='NUM'
            , constructors=[
                  IConstructor('N', 0) # Nullary
                , IConstructor('M', 0) # A distinct nullary, to test choices.
                , IConstructor('U', 1) # Unary
                , IConstructor('B', 2) # Binary
                ]
            )
        ]
    , functions=[
        IFunction('ZN', 0, [Return(Applic('bootstrap.N'))])
      , IFunction('ZF', 0, [Return(Applic('_System.Failure'))])
      , IFunction('ZQ', 0, [Return(Applic('_System.Choice', [Applic('bootstrap.N'), Applic('bootstrap.M')]))])
      , IFunction('ZW', 0, [Return(Applic('_System.Fwd', [Applic('bootstrap.N')]))])
        # Evaluates its argument and then returns a FWD node refering to it.
      , IFunction('Z' , 1, [
            Declare(Variable(vid=1, scope=ILhs(index=["bootstrap.Z", 1])))
          , ATable(0, True, Reference(1)
              , [
                    ("bootstrap.N", [Return(Reference(1))])
                  , ("bootstrap.M", [Return(Reference(1))])
                    # U,B -> failure
                  ]
              )
          ])
      ]
    )

class TestPyRuntime(cytest.TestCase):
  '''Tests for the Python runtime functions.'''
  @classmethod
  def setUpClass(cls):
    cls.BOOTSTRAP = getbootstrap()

  @classmethod
  def tearDownClass(cls):
    del cls.BOOTSTRAP

  def testCoverage(self):
    '''Tests to improve line coverage.'''
    interp = Interpreter()
    prelude = interp.import_(Prelude)
    system = interp.import_(System)
    self.assertEqual(str(prelude.negate), 'TypeInfo for "Prelude.negate"')
    self.assertEqual(str(prelude.negate.info), 'Info for "negate"')
    self.assertTrue(repr(prelude.negate.info).startswith('InfoTable'))

    n = runtime.Node(prelude.negate.info)
    self.assertRaisesRegexp(RuntimeError, 'unhandled type: str', lambda: n['foo'])
    self.assertRaisesRegexp(RuntimeError, 'unhandled type: float', lambda: n[1.])

    self.assertRaisesRegexp(
        TypeError
      , r'cannot construct "Int" \(arity=1\), with 2 args'
      , lambda: interp.expr(prelude.Int, 1, 2)
      )
    self.assertRaisesRegexp(
        TypeError
      , r'cannot construct "Choice" \(arity=2\), with 1 arg'
      , lambda: interp.expr(system.Choice, 1)
      )
    self.assertRaisesRegexp(
        TypeError, r'cannot import type "int"', lambda: interp.import_(1)
      )


  def testNormalization(self):
    '''
    Tests the built-in normalizing function (nf) applied to constructors.

    This test uses constructors N (nullary), U (unary), and B (binary) to build
    sample expression.  The assumption is that 0- and 1-argument cases are
    corners.  The 2-argument tests are intended to cover multiple-successor
    usage.

    A few functions are used to test the behavior when a new symbol arises.
    Function ZN rewrite to N and is used to check that ``nf`` properly reduces
    function symbols found under constructors.  Three additional functions
    rewrite to failure (ZF), choice (ZQ), and a forward node (ZW).  These test
    the behavior when a special symbol is uncovered while normalizing a
    constructor.
    '''
    interp_debug = Interpreter(flags={'debug':True})
    self.checkNormalization(interp_debug)
    #
    interp_nodebug = Interpreter(flags={'debug':False})
    self.checkNormalization(interp_nodebug)


  def checkNormalization(self, interp):
    bs = interp.import_(self.BOOTSTRAP)
    N,M,U,B,Z,ZN,ZF,ZQ,ZW = bs.N, bs.M, bs.U, bs.B, bs.Z, bs.ZN, bs.ZF, bs.ZQ, bs.ZW
    prelude = interp.import_(Prelude)
    system = interp.import_(System)
    F,Q,W = system.Failure, system.Choice, system.Fwd
    special_tags = [runtime.T_FAIL, runtime.T_CHOICE]

    TESTS = {
      # [rec=0] Tests for head normalization.
          #  input     output
          #  -------   ------
        0: [
            [1      ,  1     ]
          , [N      ,  N     ]
          , [[U, ZN], [U, ZN]]
          , [ZN     ,  N     ]
          # Failure
          , [F      ,  F]
          , [ZF     ,  F]
          # Choice
          , [[Q, 0, 1],  [Q, 0, 1]]
          , [ZQ,  [Q, N, M]]
          # Fwd
          , [[W, N]      ,  [W, N]]
          , [[W, ZN]     ,  [W, N]]  # The target of W is the head.
          , [[W, [W, ZN]],  [W, N]]  # Successive W nodes are contracted.
          ]
      # [rec=1] Tests for successor normalization.
      , 1: [
          # Values.
            [1        ,  1       ]
          , [N        ,  N       ]
          , [[U, N]   , [U, N]   ]
          , [[B, N, N], [B, N, N]]
          # Successor step.
          , [[U, ZN]         , [U, N]         ]
          , [[B, ZN, ZN]     , [B, N, N]      ]
          , [[B, N, ZN]      , [B, N, N]      ]
          , [[B, ZN, [U, ZN]], [B, N, [U, ZN]]]
          # Failure.
          , [[U, F]     , F]
          , [[B, N, F]  , F]
          , [[B, ZN, F] , F]
          , [[B, ZF, ZN], F]
          # Choice.
          , [[U, [Q, 0, 1]]    , [Q, [U, 0], [U, 1]]        ] # pull tab.
          , [[U, ZQ]           , [Q, [U, N], [U, M]]        ]
          , [[B, [Q, 0, 1], ZQ], [Q, [B, 0, ZQ], [B, 1, ZQ]]] # N stops at the first choice.
          , [[B, ZQ, ZQ]       , [Q, [B, N, ZQ], [B, M, ZQ]]]
          # Fwd.
          , [[U, [W, N]]          , [U, N]                  ]
          , [[U, [W, ZN]]         , [U, N]                  ]
          , [[U, [W, F]]          ,  F                      ]
          , [[B, [W, ZN], [W, ZN]], [B, N, N]               ]
          , [[B, [W, N]           , [W, [W, N]]] , [B, N, N]]
            # Special symbols must not overwrite a leading FWD node.  The FWD
            # node and its target may both have referrers, so to ensure they
            # all see the same thing, the target should be updated.
          , [[W, [U, [Q, 0, 1]]]  , [W, [Q, [U, 0], [U, 1]]]]
          , [[W, [U, ZF]]         , [W, F]                  ]
          ]
      # [rec=inf] Tests for descendant normalization (i.e., full normalization).
      , float('inf'): [
          # Descendant step.
            [[U, [U, ZN]]    , [U, [U, N]]   ]
          , [[B, [U, ZN], ZN], [B, [U, N], N]]
          , [[U, [B, ZN, ZN]], [U, [B, N, N]]]
          # Failure.
          , [[U, [U, ZF]]           , F]
          , [[B, [U, N], [B, ZF, N]], F]
          # Choice.
          , [[B, [W, ZN], [U, [U, [Q, 0, 1]]]], [Q, [B, N, [U, [U, 0]]], [B, N, [U, [U, 1]]]]]
          # Fwd.
            # Repeated W nodes are contracted, but the leading one should not
            # be removed (see note above in the rec=1 section).
          , [[W, [W, [W, [U, [B, ZN, ZN]]]]], [W, [U, [B, N, N]]]]

          # Coverage
          # Most cases are covered above.  Based on coverage analysis, we still
          # need the following additional tests: while head-normalizing a
          # function symbol, another function appears in a needed postition and
          # rewrites to  a Failure, Choice, or FWD node.
          , [[Z, ZF], F]
            # The step function aborts when the choice reaches the root position.
          , [[Z, ZQ], [Q, [Z, N], [Z, M]]]
          , [[Z, ZW], [W, N]]
          ]
      }
    for rec, testlist in TESTS.items():
      # Normalizes up to ``rec`` recursions.
      N = lambda *args, **kwds: interp.nf(*args, rec=rec, **kwds)
      for expr, expected in testlist:
        # Build the expression, normalize it the specified amount, then check
        # (1) that the modified expression matches the expected result and (2)
        # that E_SYMBOL was raised if and only if the result head symbol is a
        # failure or choice.
        expr = interp.expr(expr)
        expected = interp.expr(expected)
        try:
          N(expr)
        except runtime.E_SYMBOL:
          exc = True
        else:
          exc = False
        self.assertEqual(str(expr), str(expected)) # (1)
        self.assertEqual(exc, expected[()].info.tag in special_tags) # (2)


  def testPullTab(self):
    '''Tests the pull-tab step.'''
    pass


class TestPyInterp(cytest.TestCase):
  '''
  Tests for interpreting Curry with the Python target.
  '''
  @classmethod
  def setUpClass(cls):
    cls.ONECURRY = parse(gzip.open('data/json/1.json.gz', 'rb').read())
    cls.MYLIST = IModule(
        name='mylist', imports=[], functions=[]
      , types=[
            IType(
                ident='List'
              , constructors=[
                  IConstructor('Cons', 2, metadata={'py.format':listformat})
                , IConstructor('Nil', 0, metadata={'py.format':listformat})
                ]
              )
          ]
      )
    cls.X = IModule(
        name='X', imports=[], functions=[]
      , types=[
            IType(
                ident='X'
              , constructors=[IConstructor('X', 1)]
              )
          ]
      )
    cls.BOOTSTRAP = getbootstrap()

  @classmethod
  def tearDownClass(cls):
    del cls.ONECURRY
    del cls.MYLIST
    del cls.X
    del cls.BOOTSTRAP

  def testImportICurry(self):
    icur = self.ONECURRY
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

  def testExpr(self):
    '''Use Interpreter.expr to build expressions.'''
    interp = Interpreter()

    # Int.
    one = interp.expr(1)
    self.assertEqual(repr(one), '<Int [1]>')
    self.assertEqual(str(one), '1')

    # Float.
    pi = interp.expr(3.14)
    self.assertEqual(repr(pi), '<Float [3.14]>')
    self.assertEqual(str(pi), '3.14')

    # Node.
    example = interp.import_(self.ONECURRY)[0]
    A = interp.expr(example.A)
    self.assertEqual(repr(A), '<A []>')
    self.assertEqual(str(A), 'A')

    # Nodes with nonzero arity.
    mylist = interp.import_(self.MYLIST)
    nil = interp.expr(mylist.Nil)
    self.assertEqual(repr(nil), '<Nil []>')
    self.assertEqual(str(nil), '[]')
    #
    cons = interp.expr(mylist.Cons, 1, mylist.Nil)
    self.assertEqual(repr(cons), '<Cons [<Int [1]>, <Nil []>]>')
    self.assertEqual(str(cons), '[1]')
    #
    cons = interp.expr(mylist.Cons, 0, cons)
    self.assertEqual(str(cons), '[0, 1]')

    # Nested data specifications.
    list2 = interp.expr(mylist.Cons, 0, [mylist.Cons, 1, mylist.Nil])
    self.assertEqual(cons, list2)
    list3 = interp.expr(mylist.Cons, 1, [mylist.Cons, 2, mylist.Nil])
    self.assertNotEqual(list2, list3)

    # Negative tests.
    self.assertRaisesRegexp(
        TypeError
      , r'cannot build a Curry expression from type "dict"'
      , lambda: interp.expr({})
      )

  def testBuiltinPreludeTypes(self):
    '''
    Tests the built-in types defined in python/interpreter/prelude.py.
    Also tests the ``isa`` function.
    '''
    interp = Interpreter()
    prelude = interp.import_(Prelude)
    e2s = lambda expr: str(interp.eval(expr).next())

    # Int, Char, Float.
    Int = getattr(prelude, 'Int')
    Char = getattr(prelude, 'Char')
    Float = getattr(prelude, 'Float')
    int_ = interp.eval(1).next()
    char_ = interp.eval('a').next()
    float_ = interp.eval(1.).next()

    self.assertIsa(int_, Int)
    self.assertIsNotA(int_, Char)
    self.assertIsNotA(int_, Float)
    self.assertIsNotA(char_, Int)
    self.assertIsa(char_, Char)
    self.assertIsNotA(char_, Float)
    self.assertIsNotA(float_, Int)
    self.assertIsNotA(float_, Char)
    self.assertIsa(float_, Float)

    # List.
    Cons,Nil = getattr(prelude, ':'), getattr(prelude, '[]')
    self.assertEqual(e2s([Cons, 1, Nil]), '[1]')
    self.assertEqual(e2s([Cons, 1, [Cons, 2, Nil]]), '[1, 2]')
    l0 = Nil()
    l1 = Cons(1, l0)
    self.assertIsa(l0, interp.symbol('Prelude.[]'))
    self.assertIsNotA(l0, interp.symbol('Prelude.:'))
    self.assertIsa(l0, interp.type('Prelude.List'))
    self.assertIsa(l1, interp.type('Prelude.List'))
    self.assertIsNotA(int_, interp.type('Prelude.List'))
    # TODO: design and test .topy() and .frompy() (I guess that's just
    #     Interprerter.expr; maybe frompy is a better name?).

    # Tuples.
    Unit = getattr(prelude, '()')
    self.assertEqual(e2s([Unit]), '()')
    Pair = getattr(prelude, '(,)')
    self.assertEqual(e2s([Pair, 1, 2]), '(1, 2)')
    T = getattr(prelude, '(,,)')
    self.assertEqual(e2s([T, 1, 2, 3]), '(1, 2, 3)')
    T = getattr(prelude, '(,,,)')
    self.assertEqual(e2s([T, 1, 2, 3, 4]), '(1, 2, 3, 4)')
    T = getattr(prelude, '(,,,,)')
    self.assertEqual(e2s([T, 1, 2, 3, 4, 5]), '(1, 2, 3, 4, 5)')
    T = getattr(prelude, '(,,,,,)')
    self.assertEqual(e2s([T, 1, 2, 3, 4, 5, 6]), '(1, 2, 3, 4, 5, 6)')
    T = getattr(prelude, '(,,,,,,)')
    self.assertEqual(e2s([T, 1, 2, 3, 4, 5, 6, 7]), '(1, 2, 3, 4, 5, 6, 7)')
    T = getattr(prelude, '(,,,,,,,)')
    self.assertEqual(e2s([T, 1, 2, 3, 4, 5, 6, 7, 8]), '(1, 2, 3, 4, 5, 6, 7, 8)')
    T = getattr(prelude, '(,,,,,,,,)')
    self.assertEqual(e2s([T, 1, 2, 3, 4, 5, 6, 7, 8, 9]), '(1, 2, 3, 4, 5, 6, 7, 8, 9)')

    # Bool.
    T,F = getattr(prelude, 'True'), getattr(prelude, 'False')
    self.assertEqual(e2s([Cons, T, [Cons, F, Nil]]), '[True, False]')

  def testPreludeExternals(self):
    '''
    Tests the externally-defined functions defined in
    python/interpreter/prelude.py.
    '''
    interp = Interpreter()
    p = interp.import_(Prelude)
    self.assertEqual(interp.eval([getattr(p, '*'), 3, 4]).next(), interp.expr(12))
    self.assertEqual(interp.eval([getattr(p, '+'), 3, 4]).next(), interp.expr(7))
    self.assertEqual(interp.eval([getattr(p, '-'), 3, 4]).next(), interp.expr(-1))
    self.assertEqual(interp.eval([getattr(p, '=='), 3, 4]).next(), interp.expr(False))
    self.assertEqual(interp.eval([getattr(p, '=='), 3, 3]).next(), interp.expr(True))
    self.assertEqual(interp.eval([getattr(p, '/='), 3, 4]).next(), interp.expr(True))
    self.assertEqual(interp.eval([getattr(p, '/='), 3, 3]).next(), interp.expr(False))
    self.assertEqual(interp.eval([getattr(p, '<'), 3, 4]).next(), interp.expr(True))
    self.assertEqual(interp.eval([getattr(p, '>'), 3, 4]).next(), interp.expr(False))
    self.assertEqual(interp.eval([getattr(p, '<='), 3, 4]).next(), interp.expr(True))
    self.assertEqual(interp.eval([getattr(p, '>='), 3, 4]).next(), interp.expr(False))
    self.assertEqual(interp.eval([getattr(p, '&&'), True, True]).next(), interp.expr(True))
    self.assertEqual(interp.eval([getattr(p, '&&'), False, True]).next(), interp.expr(False))
    self.assertEqual(interp.eval([getattr(p, '||'), False, False]).next(), interp.expr(False))
    self.assertEqual(interp.eval([getattr(p, '||'), True, False]).next(), interp.expr(True))
    self.assertEqual(interp.eval([getattr(p, 'negate'), 4]).next(), interp.expr(-4))
    self.assertEqual(interp.eval([getattr(p, 'div'), 13, 5]).next(), interp.expr(2))
    self.assertEqual(interp.eval([getattr(p, 'div'), -15, 4]).next(), interp.expr(-4))
    self.assertEqual(interp.eval([getattr(p, 'mod'), 13, 5]).next(), interp.expr(3))
    self.assertEqual(interp.eval([getattr(p, 'mod'), -15, 4]).next(), interp.expr(1))
    self.assertEqual(interp.eval([getattr(p, 'quot'), 13, 5]).next(), interp.expr(2))
    self.assertEqual(interp.eval([getattr(p, 'quot'), -15, 4]).next(), interp.expr(-3))
    self.assertEqual(interp.eval([getattr(p, 'rem'), 13, 5]).next(), interp.expr(3))
    self.assertEqual(interp.eval([getattr(p, 'rem'), -15, 4]).next(), interp.expr(-3))
    self.assertEqual(interp.eval([getattr(p, 'prim_negateFloat'), 3.14]).next(), interp.expr(-3.14))

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

  @unittest.skip('need to implement Prelude')
  def testKielExamples(self):
    '''Run example programs from Kiel.'''
    for jsonfile in glob('data/json/kiel-*.json*'):
      print jsonfile
      try:
        icur = parse(gzip.open(jsonfile, 'rb').read())
        interp = Interpreter()
        mod = interp.import_(icur)
      except Exception as e:
        print 'Error>', str(e)
        continue
      print '\n\n\n\IT WORKED\n\n\n\n'
      breakpoint()

