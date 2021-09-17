import cytest # from ./lib; must be first
from cStringIO import StringIO
from curry.backends.py.runtime.graph import Node
from curry.backends.py.runtime.graph import equality
from curry import config
import curry
import cytest.step
import sys
import unittest

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
    e2s = lambda expr: str(curry.eval(expr).next())

    # Int, Char, Float.
    Int = curry.symbol('Prelude.Int')
    Char = curry.symbol('Prelude.Char')
    Float = curry.symbol('Prelude.Float')
    int_ = curry.eval(1, converter=None).next()
    char_ = curry.eval('a', converter=None).next()
    float_ = curry.eval(1., converter=None).next()

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

  def testPrimitiveBuiltins(self):
    '''Tests the built-ins over primitive types.'''
    # Note that in ALL cases below, the arguments are in reverse order.  This
    # changed in the Prelude at some point.
    eval_ = lambda e: curry.eval(e[:1] + e[1:][::-1], converter=None)
    sym = lambda s: curry.symbol('Prelude.' + s)
    # For the PAKCS prelude.
    self.assertEqual(eval_([sym('prim_plusInt'), 3, 4]).next(), curry.expr(7))
    self.assertEqual(eval_([sym('prim_minusInt'), 3, 4]).next(), curry.expr(-1))
    self.assertEqual(eval_([sym('prim_timesInt'), 3, 4]).next(), curry.expr(12))
    self.assertEqual(eval_([sym('prim_plusFloat'), 3.25, 4.]).next(), curry.expr(7.25))
    self.assertEqual(eval_([sym('prim_minusFloat'), 3.25, 4.5]).next(), curry.expr(-1.25))
    self.assertEqual(eval_([sym('prim_timesFloat'), 3.5, 4.5]).next(), curry.expr(15.75))
    self.assertEqual(eval_([sym('prim_divFloat'), 8.75, 3.5]).next(), curry.expr(2.5))
    self.assertEqual(eval_([sym('prim_negateFloat'), 3.25]).next(), curry.expr(-3.25))
    self.assertEqual(eval_([sym('prim_eqInt'), 3, 4]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('prim_eqInt'), 3, 3]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('prim_eqChar'), 'a', 'b']).next(), curry.expr(False))
    self.assertEqual(eval_([sym('prim_eqChar'), 'a', 'a']).next(), curry.expr(True))
    self.assertEqual(eval_([sym('prim_eqFloat'), 3.25, 3.5]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('prim_eqFloat'), 3.25, 3.25]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('prim_ltEqInt'), 3, 4]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('prim_ltEqInt'), 3, 3]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('prim_ltEqInt'), 3, 2]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('prim_ltEqChar'), 'b', 'c']).next(), curry.expr(True))
    self.assertEqual(eval_([sym('prim_ltEqChar'), 'b', 'b']).next(), curry.expr(True))
    self.assertEqual(eval_([sym('prim_ltEqChar'), 'b', 'a']).next(), curry.expr(False))
    self.assertEqual(eval_([sym('prim_ltEqFloat'), 3.25, 3.5]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('prim_ltEqFloat'), 3.25, 3.25]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('prim_ltEqFloat'), 3.25, 3.0]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('prim_divInt'), 13, 5]).next(), curry.expr(2))
    self.assertEqual(eval_([sym('prim_divInt'), -15, 4]).next(), curry.expr(-4))
    self.assertEqual(eval_([sym('prim_modInt'), 13, 5]).next(), curry.expr(3))
    self.assertEqual(eval_([sym('prim_modInt'), -15, 4]).next(), curry.expr(1))
    self.assertEqual(eval_([sym('prim_quotInt'), 13, 5]).next(), curry.expr(2))
    self.assertEqual(eval_([sym('prim_quotInt'), -15, 4]).next(), curry.expr(-3))
    self.assertEqual(eval_([sym('prim_remInt'), 13, 5]).next(), curry.expr(3))
    self.assertEqual(eval_([sym('prim_remInt'), -15, 4]).next(), curry.expr(-3))
    self.assertEqual(eval_([sym('prim_ord'), 'A']).next(), curry.expr(65))
    self.assertEqual(eval_([sym('prim_chr'), 65]).next(), curry.expr('A'))
    self.assertEqual(eval_([sym('prim_intToFloat'), 1]).next(), curry.expr(1.0))

    # For the KiCS2 prelude.
    self.assertEqual(eval_([sym('plusInt'), 4, 3]).next(), curry.expr(7))
    self.assertEqual(eval_([sym('minusInt'), 4, 3]).next(), curry.expr(-1))
    self.assertEqual(eval_([sym('timesInt'), 4, 3]).next(), curry.expr(12))
    self.assertEqual(eval_([sym('prim_plusFloat'), 3.25, 4.]).next(), curry.expr(7.25))
    self.assertEqual(eval_([sym('prim_minusFloat'), 3.25, 4.5]).next(), curry.expr(-1.25))
    self.assertEqual(eval_([sym('prim_timesFloat'), 3.5, 4.5]).next(), curry.expr(15.75))
    self.assertEqual(eval_([sym('prim_divFloat'), 8.75, 3.5]).next(), curry.expr(2.5))
    self.assertEqual(eval_([sym('prim_negateFloat'), 3.25]).next(), curry.expr(-3.25))
    self.assertEqual(eval_([sym('eqInt'), 4, 3]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('eqInt'), 3, 3]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('prim_eqChar'), 'a', 'b']).next(), curry.expr(False))
    self.assertEqual(eval_([sym('prim_eqChar'), 'a', 'a']).next(), curry.expr(True))
    self.assertEqual(eval_([sym('prim_eqFloat'), 3.25, 3.5]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('prim_eqFloat'), 3.25, 3.25]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('ltEqInt'), 4, 3]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('ltEqInt'), 3, 3]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('ltEqInt'), 2, 3]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('prim_ltEqChar'), 'b', 'c']).next(), curry.expr(True))
    self.assertEqual(eval_([sym('prim_ltEqChar'), 'b', 'b']).next(), curry.expr(True))
    self.assertEqual(eval_([sym('prim_ltEqChar'), 'b', 'a']).next(), curry.expr(False))
    self.assertEqual(eval_([sym('prim_ltEqFloat'), 3.25, 3.5]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('prim_ltEqFloat'), 3.25, 3.25]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('prim_ltEqFloat'), 3.25, 3.0]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('divInt'), 5, 13]).next(), curry.expr(2))
    self.assertEqual(eval_([sym('divInt'), 4, -15]).next(), curry.expr(-4))
    self.assertEqual(eval_([sym('modInt'), 5, 13]).next(), curry.expr(3))
    self.assertEqual(eval_([sym('modInt'), 4, -15]).next(), curry.expr(1))
    self.assertEqual(eval_([sym('quotInt'), 5, 13]).next(), curry.expr(2))
    self.assertEqual(eval_([sym('quotInt'), 4, -15]).next(), curry.expr(-3))
    self.assertEqual(eval_([sym('remInt'), 5, 13]).next(), curry.expr(3))
    self.assertEqual(eval_([sym('remInt'), 4, -15]).next(), curry.expr(-3))
    self.assertEqual(eval_([sym('prim_ord'), 'A']).next(), curry.expr(65))
    self.assertEqual(eval_([sym('prim_chr'), 65]).next(), curry.expr('A'))
    self.assertEqual(eval_([sym('prim_intToFloat'), 1]).next(), curry.expr(1.0))

    # Not primitive:
    eval2 = lambda e: curry.eval([sym('apply'), [sym('apply'), e[0], e[1]], e[2]])
    inst = lambda s, cls: curry.symbol('Prelude._impl#%s#Prelude.%s#Prelude.Int' % (s, cls))
    self.assertEqual(eval_([inst('divMod', 'Integral'), 5, 13]).next(), curry.expr((2,3)))
    self.assertEqual(eval_([inst('divMod', 'Integral'), 4, -15]).next(), curry.expr((-4,1)))
    self.assertEqual(eval_([inst('quotRem', 'Integral'), 5, 13]).next(), curry.expr((2,3)))
    self.assertEqual(eval_([inst('quotRem', 'Integral'), 4, -15]).next(), curry.expr((-3,-3)))
    self.assertEqual(eval_([inst('==', 'Eq'), 4, 3]).next(), curry.expr(False))
    self.assertEqual(eval_([inst('==', 'Eq'), 3, 3]).next(), curry.expr(True))
    self.assertEqual(eval2([inst('/=', 'Eq'), 4, 3]).next(), curry.expr(True))
    self.assertEqual(eval2([inst('/=', 'Eq'), 3, 3]).next(), curry.expr(False))
    self.assertEqual(eval2([inst('<', 'Ord'), 3, 4]).next(), curry.expr(True))
    self.assertEqual(eval2([inst('<', 'Ord'), False, True]).next(), curry.expr(True))
    self.assertEqual(eval2([inst('>', 'Ord'), 3, 4]).next(), curry.expr(False))
    self.assertEqual(eval2([inst('<=', 'Ord'), 3, 4]).next(), curry.expr(True))
    self.assertEqual(eval2([inst('>=', 'Ord'), 3, 4]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('&&'), True, True]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('&&'), True, False]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('||'), False, False]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('||'), False, True]).next(), curry.expr(True))
    self.assertEqual(eval_([inst('negate', 'Num'), 4]).next(), curry.expr(-4))

  def testLitParsers(self):
    eval_ = lambda e: curry.eval(e, converter=None)
    sym = lambda s: curry.symbol('Prelude.' + s)
    # Int
    self.assertEqual(eval_([sym('prim_readNatLiteral'), ['0']]).next(), curry.expr((0, "")))
    self.assertEqual(eval_([sym('prim_readNatLiteral'), "123 foo"]).next(), curry.expr((123, " foo")))
    self.assertEqual(eval_([sym('prim_readNatLiteral'), "-1"]).next(), curry.expr((0, "-1")))
    # Float
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "1.23 foo"]).next(), curry.expr((1.23, " foo")))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "+1.23 foo"]).next(), curry.expr((1.23, " foo")))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "-1.23 foo"]).next(), curry.expr((-1.23, " foo")))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "1. foo"]).next(), curry.expr((1.0, " foo")))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "1foo"]).next(), curry.expr((1.0, "foo")))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "+.9 foo"]).next(), curry.expr((0.9, " foo")))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "1.2.3"]).next(), curry.expr((1.2, ".3")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'a'xx"]).next(), curry.expr(('a', "xx")))
    # Char
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\\''xx"]).next(), curry.expr(('\'', "xx")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\\\'"]).next(), curry.expr(('\\', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\''"]).next(), curry.expr(('\'', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\\"'"]).next(), curry.expr(('"', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\b'"]).next(), curry.expr(('\b', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\f'"]).next(), curry.expr(('\f', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\n'"]).next(), curry.expr(('\n', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\r'"]).next(), curry.expr(('\r', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\t'"]).next(), curry.expr(('\t', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\v'"]).next(), curry.expr(('\v', "")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\x41'xx"]).next(), curry.expr(('A', "xx")))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\65'xx"]).next(), curry.expr(('A', "xx")))
    # String
    self.assertEqual(eval_([sym('prim_readStringLiteral'), '''"A"xx''']).next(), curry.expr(('A', "xx")))
    self.assertEqual(eval_([sym('prim_readStringLiteral'), '''"\\x41\\66""xx''']).next(), curry.expr(('AB', "\"xx")))
    self.assertEqual(eval_([sym('prim_readStringLiteral'), '''"\\\\ \\' \\" \\b \\f \\n \\r \\t \\v" tail''']).next()
      , curry.expr(('\\ \' " \b \f \n \r \t \v', " tail"))
      )

  @unittest.expectedFailure
  def testApply(self):
    add = curry.symbol('Prelude.+')
    apply_ = curry.symbol('Prelude.apply')
    #
    e = curry.expr(apply_, [apply_, add, 1], 2)
    self.assertEqual(str(e), 'apply (apply (_PartApplic 2 +) 1) 2')
    self.assertEqual(curry.eval(e).next(), 3)
    #
    incr = curry.expr(add, 1)
    self.assertEqual(str(incr), '_PartApplic 1 (+ 1)')
    e = curry.expr(apply_, incr, 6)
    self.assertEqual(curry.eval(e).next(), 7)

  def testFailed(self):
    failed = curry.symbol('Prelude.failed')
    self.assertEqual(len(list(curry.eval(failed))), 0)

  def testError(self):
    error = curry.symbol('Prelude.error')
    self.assertRaisesRegexp(
        RuntimeError, 'oops', lambda: next(curry.eval(error, "oops"))
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
    goal = interp.expr(code.goal)
    step2 = interp.expr(code.step2)
    cytest.step.step(interp, step2)
    cytest.step.step(interp, goal, num=2)
    self.assertEqual(goal, step2)

    # Ensure results are ungrounded.
    freevar = interp.compile('id $!! (x::Int) where x free', mode='expr')
    cytest.step.step(interp, freevar, num=3)
    self.assertIsaFreevar(freevar.fwd)

  # Used by testEqualityConstraint.
  def checkSatisfied(self, lhs, rhs):
    e = curry.expr(self.constrEq, lhs, rhs)
    self.assertEqual(list(curry.eval(e)), [True])

  def checkUnsatisfied(self, lhs, rhs):
    e = curry.expr(self.constrEq, lhs, rhs)
    self.assertEqual(list(curry.eval(e)), [])

  def checkError(self, lhs, rhs, type=curry.InstantiationError):
    e = curry.expr(self.constrEq, lhs, rhs)
    self.assertRaises(type, lambda: next(curry.eval(e)))

  @cytest.with_flags(defaultconverter='topython')
  def testEqualityConstraint(self):
    '''Test =:=.'''
    interp = curry.getInterpreter()
    unboxed = curry.unboxed
    # Note: a type dictionary is needed to call Prelude.unknown, but the type
    # is irrelevant for these tests.
    inst_unit = curry.symbol('Prelude._inst#Prelude.Data#()')
    unknown = curry.expr([interp.prelude.unknown, inst_unit])

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

