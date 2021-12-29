import cytest # from ./lib; must be first
from curry.backends.py.runtime.graph import Node, equality
from curry import config, inspect
from six.moves import cStringIO as StringIO
import curry, cytest.step, sys, unittest

class TestPrelude(cytest.TestCase):
  @property
  def constrEq(self):
    if config.syslibversion() < (3,3,0):
      return curry.symbol('Prelude.=:=')
    else:
      return curry.symbol('Prelude.constrEq')

  @cytest.with_flags(defaultconverter='topython')
  def testBuiltinPreludeTypes(self):
    '''
    Tests the built-in Prelude types and, indicentally, the ``isa`` function.
    '''
    e2s = lambda expr: str(next(curry.eval(expr)))

    # Int, Char, Float.
    Int = curry.symbol('Prelude.Int')
    Char = curry.symbol('Prelude.Char')
    Float = curry.symbol('Prelude.Float')
    int_ = next(curry.eval(1, converter=None))
    char_ = next(curry.eval('a', converter=None))
    float_ = next(curry.eval(1., converter=None))

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
    Cons,Nil = curry.symbol('Prelude.:'), curry.symbol('Prelude.[]')
    self.assertEqual(e2s([Cons, 1, Nil]), '[1]')
    self.assertEqual(e2s([Cons, 1, [Cons, 2, Nil]]), '[1, 2]')
    l0 = Node(Nil)
    l1 = Node(Cons, 1, l0)
    self.assertIsa(l0, curry.symbol('Prelude.[]'))
    self.assertIsNotA(l0, curry.symbol('Prelude.:'))
    self.assertIsa(l0, curry.type('Prelude.[]'))
    self.assertIsa(l1, curry.type('Prelude.[]'))
    self.assertIsNotA(int_, curry.type('Prelude.[]'))

    # Tuples.
    Unit = curry.symbol('Prelude.()')
    self.assertEqual(e2s([Unit]), '()')
    Pair = curry.symbol('Prelude.(,)')
    self.assertEqual(e2s([Pair, 1, 2]), '(1, 2)')
    T = curry.symbol('Prelude.(,,)')
    self.assertEqual(e2s([T, 1, 2, 3]), '(1, 2, 3)')
    T = curry.symbol('Prelude.(,,,)')
    self.assertEqual(e2s([T, 1, 2, 3, 4]), '(1, 2, 3, 4)')
    T = curry.symbol('Prelude.(,,,,)')
    self.assertEqual(e2s([T, 1, 2, 3, 4, 5]), '(1, 2, 3, 4, 5)')
    T = curry.symbol('Prelude.(,,,,,)')
    self.assertEqual(e2s([T, 1, 2, 3, 4, 5, 6]), '(1, 2, 3, 4, 5, 6)')
    T = curry.symbol('Prelude.(,,,,,,)')
    self.assertEqual(e2s([T, 1, 2, 3, 4, 5, 6, 7]), '(1, 2, 3, 4, 5, 6, 7)')
    T = curry.symbol('Prelude.(,,,,,,,)')
    self.assertEqual(e2s([T, 1, 2, 3, 4, 5, 6, 7, 8]), '(1, 2, 3, 4, 5, 6, 7, 8)')
    T = curry.symbol('Prelude.(,,,,,,,,)')
    self.assertEqual(e2s([T, 1, 2, 3, 4, 5, 6, 7, 8, 9]), '(1, 2, 3, 4, 5, 6, 7, 8, 9)')

    # Bool.
    T,F = curry.symbol('Prelude.True'), curry.symbol('Prelude.False')
    self.assertEqual(e2s([Cons, T, [Cons, F, Nil]]), '[True, False]')

  def testLitParsers(self):
    eval_ = lambda e: next(curry.eval(e, converter=None))
    sym = lambda s: curry.symbol('Prelude.' + s)
    # Int
    self.assertEqual(eval_([sym('prim_readNatLiteral'), ['0']]), curry.raw_expr((0, "")))
    self.assertEqual(eval_([sym('prim_readNatLiteral'), "123 foo"]), curry.raw_expr((123, " foo")))
    self.assertEqual(eval_([sym('prim_readNatLiteral'), "-1"]), curry.raw_expr((0, "-1")))
    # Float
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "1.23 foo"]), curry.raw_expr((1.23, " foo")))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "+1.23 foo"]), curry.raw_expr((1.23, " foo")))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "-1.23 foo"]), curry.raw_expr((-1.23, " foo")))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "1. foo"]), curry.raw_expr((1.0, " foo")))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "1foo"]), curry.raw_expr((1.0, "foo")))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "+.9 foo"]), curry.raw_expr((0.9, " foo")))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "1.2.3"]), curry.raw_expr((1.2, ".3")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'a'xx"]), curry.raw_expr(('a', "xx")))
    # Char
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\\''xx"]), curry.raw_expr(('\'', "xx")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\\\'"]), curry.raw_expr(('\\', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\''"]), curry.raw_expr(('\'', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\\"'"]), curry.raw_expr(('"', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\b'"]), curry.raw_expr(('\b', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\f'"]), curry.raw_expr(('\f', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\n'"]), curry.raw_expr(('\n', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\r'"]), curry.raw_expr(('\r', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\t'"]), curry.raw_expr(('\t', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\v'"]), curry.raw_expr(('\v', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\x41'xx"]), curry.raw_expr(('A', "xx")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\65'xx"]), curry.raw_expr(('A', "xx")))
    # String
    self.assertEqual(eval_([sym('prim_readStringLiteral'), '''"A"xx''']), curry.raw_expr(('A', "xx")))
    self.assertEqual(eval_([sym('prim_readStringLiteral'), '''"\\x41\\66""xx''']), curry.raw_expr(('AB', "\"xx")))
    self.assertEqual(eval_([sym('prim_readStringLiteral'), '''"\\\\ \\' \\" \\b \\f \\n \\r \\t \\v" tail'''])
      , curry.raw_expr(('\\ \' " \b \f \n \r \t \v', " tail"))
      )

  @unittest.expectedFailure
  def testApply(self):
    add = curry.symbol('Prelude.+')
    apply_ = curry.symbol('Prelude.apply')
    #
    e = curry.raw_expr(apply_, [apply_, add, 1], 2)
    self.assertEqual(str(e), 'apply (apply (_PartApplic 2 +) 1) 2')
    self.assertEqual(next(curry.eval(e)), 3)
    #
    incr = curry.raw_expr(add, 1)
    self.assertEqual(str(incr), '_PartApplic 1 (+ 1)')
    e = curry.raw_expr(apply_, incr, 6)
    self.assertEqual(next(curry.eval(e)), 7)

  def testFailed(self):
    failed = curry.symbol('Prelude.failed')
    self.assertEqual(len(list(curry.eval(failed))), 0)

  def testError(self):
    error = curry.symbol('Prelude.error')
    self.assertRaisesRegex(
        curry.EvaluationError
      , 'oops', lambda: next(curry.eval(error, "oops"))
      )

  @cytest.with_flags(defaultconverter='topython')
  def testOrd(self):
    ord_ = curry.symbol('Prelude.ord')
    self.assertEqual(list(curry.eval(ord_, 'A')), [65])

  @cytest.with_flags(defaultconverter='topython')
  def testChr(self):
    chr_ = curry.symbol('Prelude.chr')
    self.assertEqual(list(curry.eval(chr_, 65)), ['A'])

  def test_apply_nf(self):
    '''Test the $!! operator.'''
    # Ensure the RHS argument is normalized before the function is applied.
    interp = curry.getInterpreter()
    code = interp.compile(
        '''
        f :: Int -> Int
        f 0 = 1
        goal :: Int
        goal = id $!! (f 0)
        step2 :: Int
        step2 = id $!! 1
        '''
      )
    goal = interp.raw_expr(code.goal)
    step2 = interp.raw_expr(code.step2)
    cytest.step.step(interp, step2)
    cytest.step.step(interp, goal, num=2)
    self.assertEqual(goal, step2)

    # Ensure results are ungrounded.
    freevar = interp.compile('id $!! (x::Int) where x free', mode='expr')
    cytest.step.step(interp, freevar, num=3)
    freevar = inspect.fwd_chain_target(freevar)
    self.assertIsaFreevar(freevar)

  # Used by testEqualityConstraint.
  def checkSatisfied(self, lhs, rhs):
    e = curry.raw_expr(self.constrEq, lhs, rhs)
    self.assertEqual(list(curry.eval(e)), [True])

  def checkUnsatisfied(self, lhs, rhs):
    e = curry.raw_expr(self.constrEq, lhs, rhs)
    self.assertEqual(list(curry.eval(e)), [])

  def checkError(self, lhs, rhs, type=curry.InstantiationError):
    e = curry.raw_expr(self.constrEq, lhs, rhs)
    self.assertRaises(type, lambda: next(curry.eval(e)))

  @cytest.with_flags(defaultconverter='topython')
  def testEqualityConstraint(self):
    '''Test =:=.'''
    interp = curry.getInterpreter()
    unboxed = curry.unboxed
    # Note: a type dictionary is needed to call Prelude.unknown, but the type
    # is irrelevant for these tests.
    inst_unit = curry.symbol('Prelude._inst#Prelude.Data#()')
    unknown = curry.raw_expr([interp.prelude.unknown, inst_unit])

    # First, test with no free variable constraints.
    # unboxed <=> unboxed
    self.checkSatisfied(unboxed(1), unboxed(1))
    self.checkUnsatisfied(unboxed(0), unboxed(1))
    # unboxed <=> free
    self.checkError(unboxed(1), unknown)
    # unboxed <=> ctor
    self.checkError(unboxed(0), 0)
    self.checkError(unboxed(0), 1)
    # free <=> unboxed
    self.checkError(unknown, unboxed(0))
    # ctor <=> unboxed
    self.checkError(0, unboxed(0))
    self.checkError(1, unboxed(0))
    # ctor <=> ctor
    self.checkSatisfied([], [])
    self.checkSatisfied([0], [0])
    self.checkSatisfied([0,1], [0,1])
    self.checkUnsatisfied([], [1])
    self.checkUnsatisfied([0], [1])
    self.checkUnsatisfied([0], [0,1])

    # Now, test with free variable constraints.
    # free <=> free
    self.checkSatisfied(unknown, unknown)

    # ctor <=> free
    self.checkSatisfied([], unknown)

