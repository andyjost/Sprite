import cytest # from ./lib; must be first
import curry
import unittest

class TestPyCompile(cytest.TestCase):
  '''Tests for curry.compile.'''
  def testIllegalProgram(self):
    self.assertRaisesRegexp(
        curry.CompileError
      , '.x. is undefined'
      , lambda: curry.compile('f=x')
      )

  def testIllegalMode(self):
    self.assertRaisesRegexp(
        TypeError
      , "expected mode 'module' or 'expr'"
      , lambda: curry.compile('goal=0', mode='foo')
      )

  def testModuleRedefined(self):
    curry.compile('goal=0', modulename='a')
    self.assertRaisesRegexp(
        ValueError
      , "module 'a' is already defined"
      , lambda: curry.compile('goal=0', modulename='a')
      )

  def testMissingExternalConstructorDefinition(self):
    self.assertRaisesRegexp(
        ValueError
      , "'sprite__interactive_\d+.A' has no constructors and no external definition "
        "was found."
      , lambda: curry.compile('data A')
      )

  @cytest.with_flags(defaultconverter='topython')
  def testCompileStringAsModule(self):
    '''Test dynamic module compilation.'''
    text = '''
      fib :: Int -> Int
      fib n | n < 3 = 1
            | True  = (fib (n-1)) + (fib (n-2))
    '''
    fib = curry.compile(text).fib
    eight = curry.eval([fib, 6])
    self.assertEqual(eight.next(), 8)

    # Compile another version (zero-based index this time).  Ensure each one
    # works independently.
    text2 = '''
      fib :: Int -> Int
      fib n | n < 2 = 1
            | True  = (fib (n-1)) + (fib (n-2))
    '''
    fib2 = curry.compile(text2).fib
    five = curry.eval([fib2, 4])
    self.assertEqual(five.next(), 5)
    two = curry.eval([fib, 3])
    self.assertEqual(two.next(), 2)

  @cytest.with_flags(defaultconverter='topython')
  def testCompielStringAsExpr(self):
    '''Test dynamic expression compilation.'''
    Or = curry.compile(
        '''
        or :: Int -> Int -> Int
        or 0 0 = 0
        or 1 0 = 1
        or 0 1 = 1
        or 1 1 = 1
        '''
      , modulename='Or'
      )
    e = curry.compile('Or.or 0 0', mode='expr', imports=[Or])
    self.assertEqual(next(curry.eval(e)), 0)
    e = curry.compile('Or.or 0 1', mode='expr', imports=[Or])
    self.assertEqual(next(curry.eval(e)), 1)

    # Check that ICurry-generated symbols are hidden.  There are multiple
    # symbols in .symbols, but only one at the top of the module.
    self.assertGreater(len(getattr(Or, '.symbols')), 1)
    is_public = lambda k: not (k.startswith('_') or k.startswith('.'))
    self.assertEqual(len([k for k in Or.__dict__ if is_public(k)]), 1)

  @cytest.check_expressions
  def testExprType(self):
    '''Test the exprtype argument.'''
    # 1+2
    self.assertRaisesRegexp(
        curry.CompileError
      , r'''expression '1\+2' requires a type annotation'''
      , lambda: curry.compile('1+2', mode='expr')
      )
    e = curry.compile('1+2', mode='expr', exprtype='Int')
    yield e, None \
           , '<_impl#+#Prelude.Num#Prelude.Int <Int 1> <Int 2>>' \
           , None \
           , [3]

    # 1 ? 2
    self.assertRaisesRegexp(
        curry.CompileError
      , r'''expression '1 \? 2' requires a type annotation'''
      , lambda: curry.compile('1 ? 2', mode='expr')
      )
    e = curry.compile('1 ? 2', mode='expr', exprtype='Int')
    yield e, None, '<? <Int 1> <Int 2>>', None, [[1, 2]]

  @cytest.check_expressions
  def test_reclet(self):
    e = curry.compile('''let a = True:b ; b = False:a in a''', 'expr')
    yield e, '[True, False, ...]', '<_Fwd <: <True> <: <False> ...>>>'

