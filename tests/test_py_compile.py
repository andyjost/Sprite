import cytest # from ./lib; must be first
import curry
import unittest

curry.flags['trace'] = True

class TestPyCompile(cytest.TestCase):
  def testCompileString(self):
    '''Test direct compilation of a string.'''
    text = '''
      fib n | n < 3 = 1
            | True  = (fib (n-1)) + (fib (n-2))
    '''
    fib = curry.compile(text)
    eight = curry.eval([fib.fib, 6])
    self.assertEqual(eight.next(), 8)
