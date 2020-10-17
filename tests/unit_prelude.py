import cytest # from ./lib; must be first
import cytest.step
from cStringIO import StringIO
from curry.interpreter import runtime
from import_blocker import ImportBlocker
import curry
import sys
import unittest

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
    self.assertEqual(eval_([sym('+$'), 3, 4]).next(), curry.expr(7))
    self.assertEqual(eval_([sym('-$'), 3, 4]).next(), curry.expr(-1))
    self.assertEqual(eval_([sym('*$'), 3, 4]).next(), curry.expr(12))
    self.assertEqual(eval_([sym('prim_Float_plus'), 3.25, 4.]).next(), curry.expr(7.25))
    self.assertEqual(eval_([sym('prim_Float_minus'), 3.25, 4.5]).next(), curry.expr(-1.25))
    self.assertEqual(eval_([sym('prim_Float_times'), 3.5, 4.5]).next(), curry.expr(15.75))
    self.assertEqual(eval_([sym('prim_Float_div'), 8.75, 3.5]).next(), curry.expr(2.5))
    self.assertEqual(eval_([sym('negateFloat'), 3.25]).next(), curry.expr(-3.25))
    self.assertEqual(eval_([sym('eqInt'), 3, 4]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('eqInt'), 3, 3]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('eqChar'), 'a', 'b']).next(), curry.expr(False))
    self.assertEqual(eval_([sym('eqChar'), 'a', 'a']).next(), curry.expr(True))
    self.assertEqual(eval_([sym('eqFloat'), 3.25, 3.5]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('eqFloat'), 3.25, 3.25]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('ltEqInt'), 3, 4]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('ltEqInt'), 3, 3]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('ltEqInt'), 3, 2]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('ltEqChar'), 'b', 'c']).next(), curry.expr(True))
    self.assertEqual(eval_([sym('ltEqChar'), 'b', 'b']).next(), curry.expr(True))
    self.assertEqual(eval_([sym('ltEqChar'), 'b', 'a']).next(), curry.expr(False))
    self.assertEqual(eval_([sym('ltEqFloat'), 3.25, 3.5]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('ltEqFloat'), 3.25, 3.25]).next(), curry.expr(True))
    self.assertEqual(eval_([sym('ltEqFloat'), 3.25, 3.0]).next(), curry.expr(False))
    self.assertEqual(eval_([sym('div_'), 13, 5]).next(), curry.expr(2))
    self.assertEqual(eval_([sym('div_'), -15, 4]).next(), curry.expr(-4))
    self.assertEqual(eval_([sym('mod_'), 13, 5]).next(), curry.expr(3))
    self.assertEqual(eval_([sym('mod_'), -15, 4]).next(), curry.expr(1))
    self.assertEqual(eval_([sym('quot_'), 13, 5]).next(), curry.expr(2))
    self.assertEqual(eval_([sym('quot_'), -15, 4]).next(), curry.expr(-3))
    self.assertEqual(eval_([sym('rem_'), 13, 5]).next(), curry.expr(3))
    self.assertEqual(eval_([sym('rem_'), -15, 4]).next(), curry.expr(-3))
    self.assertEqual(eval_([sym('divMod_'), 13, 5]).next(), curry.expr((2,3)))
    self.assertEqual(eval_([sym('divMod_'), -15, 4]).next(), curry.expr((-4,1)))
    self.assertEqual(eval_([sym('quotRem_'), 13, 5]).next(), curry.expr((2,3)))
    self.assertEqual(eval_([sym('quotRem_'), -15, 4]).next(), curry.expr((-3,-3)))
    self.assertEqual(eval_([sym('prim_ord'), 'A']).next(), curry.expr(65))
    self.assertEqual(eval_([sym('prim_chr'), 65]).next(), curry.expr('A'))
    self.assertEqual(eval_([sym('prim_i2f'), 1]).next(), curry.expr(1.0))

    # Not primitive:
    # self.assertEqual(eval_([sym('=='), 3, 4]).next(), curry.expr(False))
    # self.assertEqual(eval_([sym('=='), 3, 3]).next(), curry.expr(True))
    # self.assertEqual(eval_([sym('/='), 3, 4]).next(), curry.expr(True))
    # self.assertEqual(eval_([sym('/='), 3, 3]).next(), curry.expr(False))
    # self.assertEqual(eval_([sym('<'), 3, 4]).next(), curry.expr(True))
    # self.assertEqual(eval_([sym('<'), False, True]).next(), curry.expr(True))
    # self.assertEqual(eval_([sym('>'), 3, 4]).next(), curry.expr(False))
    # self.assertEqual(eval_([sym('<='), 3, 4]).next(), curry.expr(True))
    # self.assertEqual(eval_([sym('>='), 3, 4]).next(), curry.expr(False))
    # self.assertEqual(eval_([sym('&&'), True, True]).next(), curry.expr(True))
    # self.assertEqual(eval_([sym('&&'), False, True]).next(), curry.expr(False))
    # self.assertEqual(eval_([sym('||'), False, False]).next(), curry.expr(False))
    # self.assertEqual(eval_([sym('||'), True, False]).next(), curry.expr(True))
    # self.assertEqual(eval_([sym('negate'), 4]).next(), curry.expr(-4))

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

  def testOrd(self):
    ord_ = curry.symbol('Prelude.ord')
    self.assertEqual(list(curry.eval(ord_, 'A')), [65])

  def testChr(self):
    chr_ = curry.symbol('Prelude.chr')
    self.assertEqual(list(curry.eval(chr_, 65)), ['A'])

  @cytest.setio(stdin='muh\ninput\n')
  def test_getChar(self):
    getChar = curry.symbol('Prelude.getChar')
    self.assertEqual(list(curry.eval(getChar)), ['m'])

  @cytest.setio(stdout='')
  def test_putChar(self):
    putChar = curry.symbol('Prelude.putChar')
    IO = curry.symbol('Prelude.IO')
    Unit = curry.symbol('Prelude.()')
    self.assertEqual(list(curry.eval(putChar, 'x')), [curry.expr(IO, Unit)])
    self.assertEqual(curry.getInterpreter().stdout.getvalue(), 'x')

  def test_readFile(self):
    readFile = curry.symbol('Prelude.readFile')
    self.assertEqual(
        list(curry.eval(readFile, "data/sample.txt"))
      , ['this is a file\ncontaining sample text\n\n(the end)\n']
      )

  def test_readFile_no_mmap(self):
    if 'mmap' in sys.modules:
      del sys.modules['mmap']
    sys.meta_path.insert(0, ImportBlocker('mmap'))
    try:
      self.test_readFile()
    finally:
      sys.meta_path[:] = sys.meta_path[1:]

  def test_apply_nf(self):
    '''Test the $!! operator.'''
    # Ensure the RHS argument is normalized before the function is applied.
    interp = curry.getInterpreter()
    code = interp.compile(
        '''
        f 0 = 1
        goal = id $!! (f 0)
        step2 = id $!! 1
        '''
      )
    goal = interp.expr(code.goal)
    step2 = interp.expr(code.step2)
    cytest.step.step(interp, step2)
    cytest.step.step(interp, goal, num=2)
    self.assertEqual(goal, step2)

    # Ensure results are ungrounded.
    freevar = interp.compile('id $!! x where x free', mode='expr')
    cytest.step.step(interp, freevar, num=3)
    self.assertTrue(curry.inspect.isa_freevar(interp, freevar))

