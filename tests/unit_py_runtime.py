import cytest # from ./lib; must be first
from copy import copy
from curry.backends.py.runtime.control import E_UNWIND
from curry.backends.py.runtime.graph import Node, equality
from curry.backends.py.runtime.state import Bindings, RuntimeState
from curry.backends.py.runtime.state.rts_freevars import _gen_ctors
from curry.common import T_FAIL, T_CHOICE
from curry import icurry, inspect, interpreter
from curry.utility.binding import binding
from cytest import bootstrap
from glob import glob
import curry.backends.py.runtime.currylib.prelude
import curry, os, unittest
import cytest.step

class TestPyRuntime(cytest.TestCase):
  '''Tests for the Python runtime functions.'''
  @classmethod
  def setUpClass(cls):
    cls.BOOTSTRAP = bootstrap.getbootstrap()

  @classmethod
  def tearDownClass(cls):
    del cls.BOOTSTRAP

  def test_coverage(self):
    '''Tests to improve line coverage.'''
    interp = interpreter.Interpreter()
    prelude = interp.prelude
    self.assertEqual(prelude.prim_negateFloat.fullname, 'Prelude.prim_negateFloat')
    self.assertEqual(str(prelude.prim_negateFloat.info), "Info for 'prim_negateFloat'")
    self.assertTrue(repr(prelude.prim_negateFloat.info).startswith('InfoTable'))

    n = Node(getattr(prelude, '()').info)
    self.assertRaisesRegex(curry.CurryIndexError, r"not 'str'", lambda: n['foo'])
    self.assertRaisesRegex(curry.CurryIndexError, r"not 'float'", lambda: n[1.])

    self.assertRaisesRegex(
        TypeError
      , r"cannot construct 'Int' \(arity=1\), with 2 args"
      , lambda: interp.raw_expr(prelude.Int, 1, 2)
      )
    self.assertRaisesRegex(
        TypeError, r"cannot import type 'int'", lambda: interp.import_(1)
      )

  def test_normalization(self):
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

  @unittest.skip('rec was removed')
  def checkNormalization(self, interp):
    bs = interp.import_(self.BOOTSTRAP)
    N,M,U,B,Z,ZN,ZF,ZQ,ZW = bs.N, bs.M, bs.U, bs.B, bs.Z, bs.ZN, bs.ZF, bs.ZQ, bs.ZW
    prelude = interp.import_(interpreter.prelude.Prelude)
    F,Q,W = prelude._Failure, prelude._Choice, prelude._Fwd
    special_tags = [T_FAIL, T_CHOICE]
    cid = bootstrap.cid

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
          , [[Q, cid, 0, 1],  [Q, cid, 0, 1]]
          , [ZQ,  [Q, cid, N, M]  ]
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
          , [[U, [Q, cid, 0, 1]]    , [Q, cid, [U, 0], [U, 1]]        ] # pull tab.
          , [[U, ZQ]           , [Q, cid, [U, N], [U, M]]             ]
          , [[B, [Q, cid, 0, 1], ZQ], [Q, cid, [B, 0, ZQ], [B, 1, ZQ]]] # N stops at the first choice.
          , [[B, ZQ, ZQ]       , [Q, cid, [B, N, ZQ], [B, M, ZQ]]     ]
          # Fwd.
          , [[U, [W, N]]          , [U, N]                            ]
          , [[U, [W, ZN]]         , [U, N]                            ]
          , [[U, [W, F]]          ,  F                                ]
          , [[B, [W, ZN], [W, ZN]], [B, N, N]                         ]
          , [[B, [W, N]           , [W, [W, N]]] , [B, N, N]          ]
            # Special symbols must not overwrite a leading FWD node.  The FWD
            # node and its target may both have referrers, so to ensure they
            # all see the same thing, the target should be updated.
          , [[W, [U, [Q, cid, 0, 1]]]  , [W, [Q, cid, [U, 0], [U, 1]]]]
          , [[W, [U, ZF]]         , [W, F]                            ]
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
          , [[B, [W, ZN], [U, [U, [Q, cid, 0, 1]]]], [Q, cid, [B, N, [U, [U, 0]]], [B, N, [U, [U, 1]]]]]
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
          , [[Z, ZQ], [Q, cid, [Z, N], [Z, M]]]
          , [[Z, ZW], [W, N]]
          ]
      }
    for rec, testlist in TESTS.items():
      # Normalizes up to ``rec`` recursions.
      N = lambda *args, **kwds: interp.nf(*args, rec=rec, **kwds)
      for expr, expected in testlist:
        # Build the expression, normalize it the specified amount, then check
        # (1) that the modified expression matches the expected result and (2)
        # that E_UNWIND was raised if and only if the result head symbol is a
        # failure or choice.
        expr = interp.raw_expr(expr)
        expected = interp.raw_expr(expected)
        try:
          N(expr)
        except E_UNWIND:
          exc = True
        else:
          exc = False
        self.assertEqual(str(expr), str(expected)) # (1)
        self.assertEqual(exc, expected[()].info.tag in special_tags) # (2)

  def test_inspect_module(self):
    module = curry.compile(
        '''
        not True = False
        not False = True
        xor False a = a
        xor True a = not a
        '''
      )
    json = inspect.getjsonfile(module)
    self.assertTrue(os.path.exists(json))
    self.assertTrue(json.endswith('.json') or json.endswith('.json.z'))
    #
    icurfile = inspect.geticurryfile(module)
    self.assertTrue(os.path.exists(icurfile))
    self.assertTrue(icurfile.endswith('.icy'))
    #
    icur = inspect.geticurry(module)
    self.assertIsInstance(icur, icurry.IModule)

  @cytest.with_flags(defaultconverter='topython')
  def test_instantiation(self):
    goal = curry.compile(
        '''
        f [True] = True
        main | f x = x where x free
        '''
      ).main
    value, = curry.eval(goal)
    self.assertEqual(str(value), '[True]')

  def test_interp_step(self):
    interp = curry.getInterpreter()
    code = interp.compile(
        '''
        f :: Int -> Int
        f 1 = 0

        g :: Int -> Int
        g 0 = 0

        goal :: Int
        goal = f (g (g 0))

        step2 :: Int
        step2 = f (g 0)

        step3 :: Int
        step3 = f 0
        '''
      )
    goal = interp.raw_expr(code.goal)
    step2 = interp.raw_expr(code.step2)
    cytest.step.step(interp, step2)
    step3 = interp.raw_expr(code.step3)
    cytest.step.step(interp, step3)
    #
    cytest.step.step(interp, goal, num=2)
    self.assertEqual(goal, step2)
    cytest.step.step(interp, goal)
    self.assertEqual(goal, step3)
    self.assertEqual(list(interp.eval(goal)), [])

  def test_getimpl(self):
    # Positive test.
    from curry.lib import hello
    self.assertRegex(hello.main.getimpl(), '^def (\w+)\(rts, _0\):\s+# hello\.main')
    # Negative test.
    self.assertRaisesRegex(
        ValueError
      , "no implementation code available for 'Prelude.True'"
      , lambda: curry.symbol('Prelude.True').getimpl()
      )

  @unittest.expectedFailure
  def test_bindings_store(self):
    '''Test the bindings object.'''
    a = Bindings()
    # a = Shared(refcnt=1, defaultdict(<function factory at ...>, {}))
    self.assertEqual(a.refcnt, 1)
    self.assertEqual(len(a.read), 0)

    a.write[0]
    # a = Shared(refcnt=1, defaultdict(<function factory at ...>, {0: Shared(refcnt=1, [])}))
    self.assertEqual(a.read.keys(), [0])
    self.assertEqual(a.read[0].refcnt, 1)
    self.assertEqual(a.read[0].read, [])

    a.write[0].write.append(1)
    # a = Shared(refcnt=1, defaultdict(<function factory at ...>, {0: Shared(refcnt=1, [1])}))
    self.assertEqual(a.read[0].read, [1])
    self.assertEqual(a.read[0].refcnt, 1)

    a.write[1].write.append(0)
    # Shared(refcnt=1, defaultdict(<function factory at ...>, {0: Shared(refcnt=1, [1]), 1: Shared(refcnt=1, [0])}))
    self.assertEqual(a.read[1].read, [0])
    self.assertEqual(a.read[1].refcnt, 1)

    b = copy(a)
    # a = Shared(refcnt=2, defaultdict(<function factory at ...>, {0: Shared(refcnt=1, [1]), 1: Shared(refcnt=1, [0])}))
    # b = Shared(refcnt=2, defaultdict(<function factory at ...>, {0: Shared(refcnt=1, [1]), 1: Shared(refcnt=1, [0])}))
    self.assertIs(a.read, b.read) # shared
    self.assertEqual(a.refcnt, 2)
    self.assertEqual(sorted(a.read.keys()), [0, 1])
    self.assertEqual(a.read[0].refcnt, 1)
    self.assertEqual(a.read[1].refcnt, 1)

    a.write
    # a = Shared(refcnt=1, defaultdict(<function factory at ...>, {0: Shared(refcnt=2, [1]), 1: Shared(refcnt=2, [0])}))
    # b = Shared(refcnt=1, defaultdict(<function factory at ...>, {0: Shared(refcnt=2, [1]), 1: Shared(refcnt=2, [0])}))
    self.assertIsNot(a.read, b.read) # no longer shared
    self.assertIs(a.read[0].read, b.read[0].read) # shared
    self.assertIs(a.read[1].read, b.read[1].read) # shared
    self.assertEqual(a.read[0].refcnt, 2) # shared
    self.assertEqual(a.read[1].refcnt, 2) # shared
    self.assertEqual(a.read[0].read, [1])
    self.assertEqual(a.read[1].read, [0])

    a.read[0].write
    # a = Shared(refcnt=2, defaultdict(<function factory at ...>, {0: Shared(refcnt=1, [1]), 1: Shared(refcnt=2, [0])}))
    # b = Shared(refcnt=2, defaultdict(<function factory at ...>, {0: Shared(refcnt=1, [1]), 1: Shared(refcnt=2, [0])}))
    self.assertIsNot(a.read[0], b.read[0]) # no longer shared
    self.assertEqual(a.read[0].refcnt, 1) # not shared
    self.assertEqual(b.read[0].refcnt, 1) # not shared
    self.assertEqual(a.read[0].read, [1])
    self.assertEqual(b.read[0].read, [1])
    self.assertIs(a.read[1].read, b.read[1].read) # still shared
    self.assertEqual(a.read[1].refcnt, 2) # shared


class TestInstantiation(cytest.TestCase):
  def setUp(self):
    super(TestInstantiation, self).setUp()
    self.interp = interpreter.Interpreter()

  def e(self, typename, imports=None):
    x, = list(self.interp.eval(self.interp.compile(
        'x::(%s) where x free' % typename, 'expr', imports=imports
      )))
    self.assertIsaFreevar(x)
    self.assertChoiceIdEquals(x, 0)
    return self.interp.raw_expr(self.interp.prelude.id, x)

  def q(self, cid, l, r):
    return [self.interp.prelude._Choice, curry.unboxed(cid), l, r]

  def u(self, rts):
    return rts.freshvar()

  def x(self, cid):
    return Node(
        self.interp.prelude._Free.info
      , cid
      , Node(self.interp.prelude.Unit.info)
      )

  def test_basic(self):
    interp,q,x,e = self.interp, self.q, self.x, self.e(typename='()')
    rts = RuntimeState(interp)
    instance = rts.instantiate(rts.variable(e, [0]), interp.type('Prelude.[]'))
    au = curry.raw_expr(*q(0, [interp.prelude.Cons, x(1), x(2)], [interp.prelude.Nil]))
    self.assertEqual(instance, au)

  def check_gen_ctors(self, interp, module, typename, generator):
    '''
    Check whether the constructors extracted from a generator by
    _gen_ctors match the constructors in the typeinfo.
    '''
    # Get the constructor info from the type.
    ctor_info = [ctor.info for ctor in getattr(module, '.types')[typename].constructors]
    # Get the constructor info from a generator.
    gen_info = list(_gen_ctors(interp, generator))
    self.assertEqual(ctor_info, gen_info)

  def test_singleCtor(self):
    # Instantiating a type with one constructor is a special case.
    interp,q,e = self.interp, self.q, self.e(typename='()')
    rts = RuntimeState(interp)
    instance = rts.instantiate(rts.variable(e, [0]), interp.type('Prelude.()'))
    au = curry.raw_expr(*q(0, [interp.prelude.Unit], [interp.prelude._Failure]))
    self.assertEqual(instance, au)
    self.check_gen_ctors(interp, interp.prelude, '()', instance)

  def test_minDepth7(self):
    '''Minimal instance depth (7 constructors).'''
    #             ?0
    #       ?1          ?4
    #    ?2    ?3    ?5    G
    #   A  B  C  D  E  F
    interp,q = self.interp, self.q
    Type = interp.compile('data T = A|B|C|D|E|F|G', modulename='Type')
    e = self.e(typename='Type.T', imports=Type)
    rts = RuntimeState(interp)
    instance = rts.instantiate(rts.variable(e, [0]), interp.type('Type.T'))
    au = curry.raw_expr(*q(0, q(1, q(2, Type.A, Type.B), q(3, Type.C, Type.D)), q(4, q(5, Type.E, Type.F), Type.G)))
    self.assertEqual(instance, au)
    self.check_gen_ctors(interp, Type, 'T', instance)

  def test_minDepth6(self):
    '''Minimal instance depth (6 constructors).'''
    #         ?0
    #      ?1     ?3
    #    ?2  C  ?4  F
    #   A  B   D  E
    interp,q = self.interp, self.q
    Type = interp.compile('data T = A|B|C|D|E|F', modulename='Type')
    e = self.e(typename='Type.T', imports=Type)
    rts = RuntimeState(interp)
    instance = rts.instantiate(rts.variable(e, [0]), interp.type('Type.T'))
    au = curry.raw_expr(*q(0, q(1, q(2, Type.A, Type.B), Type.C), q(3, q(4, Type.D, Type.E), Type.F)))
    self.assertEqual(instance, au)
    self.check_gen_ctors(interp, Type, 'T', instance)

  def test_complex(self):
    #        ?0
    #      ?1   ?3
    #    ?2  C D  E
    #   A  B
    interp,q,x = self.interp, self.q, self.x
    Type = interp.compile('data T a = A|B a|C a a|D a a a|E a a a a', modulename='Type')
    e = self.e(typename='Type.T ()', imports=Type)
    rts = RuntimeState(interp)
    instance = rts.instantiate(rts.variable(e, [0]), interp.type('Type.T'))
    au = curry.raw_expr(*q(0, q(1, q(2, Type.A, [Type.B, x(3)]), [Type.C, x(4), x(5)]), q(6, [Type.D, x(7), x(8), x(9)], [Type.E, x(10), x(11), x(12), x(13)])))
    self.assertEqual(instance, au)
    self.check_gen_ctors(interp, Type, 'T', instance)

