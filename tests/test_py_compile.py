import cytest # from ./lib; must be first
import curry
import unittest

class TestPyCompile(cytest.TestCase):
  def testCompileString(self):
    '''Test direct compilation of a string.'''
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
