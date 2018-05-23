import cytest # from ./lib; must be first
import curry
import unittest

class TestPyCompile(cytest.TestCase):
  def testCompileStringModule(self):
    '''Test dynamic module compilation.'''
    text = '''
      fib n | n < 3 = 1
            | True  = (fib (n-1)) + (fib (n-2))
    '''
    fib = curry.compile(text).fib
    eight = curry.eval([fib, 6])
    self.assertEqual(eight.next(), 8)

    # Compile another version (zero-based index this time).  Ensure each one
    # works independently.
    text2 = '''
      fib n | n < 2 = 1
            | True  = (fib (n-1)) + (fib (n-2))
    '''
    fib2 = curry.compile(text2).fib
    five = curry.eval([fib2, 4])
    self.assertEqual(five.next(), 5)
    two = curry.eval([fib, 3])
    self.assertEqual(two.next(), 2)

  def testCompielStringExpr(self):
    '''Test dynamic expression compilation.'''
    Or = curry.compile(
        '''
        or 0 0 = 0
        or 1 0 = 1
        or 0 1 = 1
        or 1 1 = 1
        '''
      , modulename='Or'
      )
    e = curry.compile('Or.or 0 0', mode='expr')
    self.assertEqual(next(curry.eval(e)), 0)
    e = curry.compile('Or.or 0 1', mode='expr')
    self.assertEqual(next(curry.eval(e)), 1)
