import cytest # from ./lib; must be first
import curry
from curry.interpreter import runtime

class TestPrelude(cytest.TestCase):
  def testBuiltinPreludeTypes(self):
    '''
    Tests the built-in Prelude types and, indicentally, the ``isa`` function.
    '''
    e2s = lambda expr: str(curry.eval(expr, converter=None).next())

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
    l0 = runtime.Node(Nil)
    l1 = runtime.Node(Cons, 1, l0)
    self.assertIsa(l0, curry.symbol('Prelude.[]'))
    self.assertIsNotA(l0, curry.symbol('Prelude.:'))
    self.assertIsa(l0, curry.type('Prelude.[]'))
    self.assertIsa(l1, curry.type('Prelude.[]'))
    self.assertIsNotA(int_, curry.type('Prelude.[]'))
    # TODO: design and test .topy() and .frompy() (I guess that's just
    #     Interprerter.expr; maybe frompy is a better name?).

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
    eval_ = lambda e: curry.eval(e, converter=None)
    sym = lambda s: curry.symbol('Prelude.' + s)
    self.assertEqual(eval_([sym('*'), 3, 4]).next(), curry.expr(12))
    self.assertEqual(eval_([sym('+'), 3, 4]).next(), curry.expr(7))
    self.assertEqual(eval_([sym('-'), 3, 4]).next(), curry.expr(-1))
    self.assertEqual(eval_([sym('=='), 3, 4]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('=='), 3, 3]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('/='), 3, 4]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('/='), 3, 3]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('<'), 3, 4]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('>'), 3, 4]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('<='), 3, 4]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('>='), 3, 4]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('&&'), True, True]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('&&'), False, True]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('||'), False, False]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('||'), True, False]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('negate'), 4]).next(), curry.expr(-4))
    self.assertEqual(eval_([sym('div'), 13, 5]).next(), curry.expr(2))
    self.assertEqual(eval_([sym('div'), -15, 4]).next(), curry.expr(-4))
    self.assertEqual(eval_([sym('mod'), 13, 5]).next(), curry.expr(3))
    self.assertEqual(eval_([sym('mod'), -15, 4]).next(), curry.expr(1))
    self.assertEqual(eval_([sym('quot'), 13, 5]).next(), curry.expr(2))
    self.assertEqual(eval_([sym('quot'), -15, 4]).next(), curry.expr(-3))
    self.assertEqual(eval_([sym('rem'), 13, 5]).next(), curry.expr(3))
    self.assertEqual(eval_([sym('rem'), -15, 4]).next(), curry.expr(-3))
    self.assertEqual(eval_([sym('prim_negateFloat'), 3.14]).next(), curry.expr(-3.14))

  def testApply(self):
    add = curry.symbol('Prelude.+')
    apply_ = curry.symbol('Prelude.apply')
    #
    e = curry.expr(apply_, [apply_, add, 1], 2)
    self.assertEqual(str(e), 'apply (apply (PartApplic 2 +) 1) 2')
    self.assertEqual(curry.eval(e).next(), 3)
    #
    incr = curry.expr(add, 1)
    self.assertEqual(str(incr), 'PartApplic 1 (+ 1)')
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

