import cytest # from ./lib; must be first
import curry
import unittest

class TestPyCompile(cytest.TestCase):
  @unittest.expectedFailure
  def testCompileString(self):
    '''Test direct compilation of a string.'''
    text = '''
      fib n | n < 2 = 1
            | True  = (fib (n-1)) + (fib (n-2))
    '''
    fib = curry.compile(text)
    eight = curry.eval(fib.fib(5)).next()
    self.assertEqual(eight, 8)
