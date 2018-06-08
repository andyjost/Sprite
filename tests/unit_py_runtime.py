import cytest # from ./lib; must be first
from curry import icurry
from curry import inspect
from curry import interpreter
from curry.interpreter import runtime
from cytest import bootstrap
from glob import glob
import curry
import curry.interpreter.prelude
import os
import unittest

class TestPyRuntime(cytest.TestCase):
  '''Tests for the Python runtime functions.'''
  @classmethod
  def setUpClass(cls):
    cls.BOOTSTRAP = bootstrap.getbootstrap()

  @classmethod
  def tearDownClass(cls):
    del cls.BOOTSTRAP

  def testCoverage(self):
    '''Tests to improve line coverage.'''
    interp = interpreter.Interpreter()
    prelude = interp.import_(interpreter.prelude.Prelude)
    self.assertEqual(str(prelude.negate), 'Prelude.negate')
    self.assertEqual(str(prelude.negate.info), 'Info for "negate"')
    self.assertTrue(repr(prelude.negate.info).startswith('InfoTable'))

    n = runtime.Node(getattr(prelude, '()').info)
    self.assertRaisesRegexp(RuntimeError, 'unhandled type: str', lambda: n['foo'])
    self.assertRaisesRegexp(RuntimeError, 'unhandled type: float', lambda: n[1.])

    self.assertRaisesRegexp(
        TypeError
      , r'cannot construct "Int" \(arity=1\), with 2 args'
      , lambda: interp.expr(prelude.Int, 1, 2)
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
    interp_debug = interpreter.Interpreter(flags={'debug':True})
    self.checkNormalization(interp_debug)
    #
    interp_nodebug = interpreter.Interpreter(flags={'debug':False})
    self.checkNormalization(interp_nodebug)


  def checkNormalization(self, interp):
    bs = interp.import_(self.BOOTSTRAP)
    N,M,U,B,Z,ZN,ZF,ZQ,ZW = bs.N, bs.M, bs.U, bs.B, bs.Z, bs.ZN, bs.ZF, bs.ZQ, bs.ZW
    prelude = interp.import_(interpreter.prelude.Prelude)
    F,Q,W = prelude._Failure, prelude._Choice, prelude._Fwd
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

  @unittest.expectedFailure
  def testPullTab(self):
    '''Tests the pull-tab step.'''
    self.assertTrue(False) # TODO


  def test_inspect_module(self):
    module = curry.compile(
        '''
        not True = False
        not False = True
        xor False a = a
        xor True a = not a
        '''
      )
    read = inspect.getreadable(module)
    self.assertTrue(os.path.exists(read))
    self.assertTrue(read.endswith('.read'))
    #
    json = inspect.getjson(module)
    self.assertTrue(os.path.exists(json))
    self.assertTrue(json.endswith('.json'))
    #
    icur = inspect.geticurry(module)
    self.assertIsInstance(icur, icurry.IModule)


  def test_nd_io(self):
    goal = curry.compile("putChar ('a' ? 'b')", 'expr')
    self.assertRaisesRegexp(
        RuntimeError
      , r'non-determinism occurred in I/O actions'
      , lambda: list(curry.eval(goal))
      )

