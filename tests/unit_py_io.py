import cytest # from ./lib; must be first
from cStringIO import StringIO
import curry
import unittest

class TestPyIO(cytest.TestCase):
  def test_ioHello(self):
    Test = curry.compile(
        '''
        main = do
            x <- return ("Hello, " ++ "World!")
            putStr x
        '''
      , modulename='Test'
      )
    stdout = StringIO()
    curry._interpreter_.stdout = stdout
    out = curry.eval([Test.main])
    result = next(out)
    self.assertEqual(stdout.getvalue(), "Hello, World!")
    self.assertEqual(str(result), 'IO ()')

  @unittest.expectedFailure
  @cytest.setio(stdout='')
  def test_nd_io(self):
    goal = curry.compile("putChar ('a' ? 'b')", 'expr')
    self.assertRaisesRegexp(
        RuntimeError
      , r'non-determinism in I/O actions occurred'
      , lambda: list(curry.eval(goal))
      )

  @unittest.expectedFailure
  @cytest.setio(stdout='')
  def test_nd_io2(self):
    goal = curry.compile('''putStrLn ("one" ? "two")''', 'expr')
    self.assertRaisesRegexp(
        RuntimeError
      , r'non-determinism in I/O actions occurred'
      , lambda: list(curry.eval(goal))
      )

