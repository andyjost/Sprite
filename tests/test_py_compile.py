import cytest # from ./lib
import unittest

class TestPyCompile(cytest.TestCase):
  @unittest.expectedFailure
  def testCompileString(self):
    '''Test direct compilation of a string.'''
    interp = Interpreter()
    text = '''
      fib n | n < 2 = 1
            | True  = (fib (n-1)) + (fib (n-2))
    '''
    fib = interp.compile(text)
    eight = interp.eval(fib.fib(5)).next()
    self.assertEqual(eight, 8)
