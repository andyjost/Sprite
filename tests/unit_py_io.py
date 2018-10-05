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

  def test_nd_io(self):
    goal = curry.compile("putChar ('a' ? 'b')", 'expr')
    self.assertRaisesRegexp(
        RuntimeError
      , r'non-determinism in I/O actions occurred'
      , lambda: list(curry.eval(goal))
      )

  # I think the fix for this is to mark IO built-ins with a special flag.
  # Then, when applying the pull-tab step, raise RuntimeError whenever
  # the source has that flag.
  #
  # Or, perhaps I just need to add this check to compose_io, return, and
  # anything else that might unwrap an IO.  Maybe even just the IO monad
  # itself.
  #
  # Maybe the pull-tab step should be provided by the info table.
  @unittest.skip('due to infinite recursion')
  @unittest.expectedFailure
  def test_nd_io2(self):
    goal = curry.compile('''putStrLn ("one" ? "two")''', 'expr')
    self.assertRaisesRegexp(
        RuntimeError
      , r'non-determinism in I/O actions occurred'
      , lambda: list(curry.eval(goal))
      )

