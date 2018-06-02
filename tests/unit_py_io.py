import cytest # from ./lib; must be first
import curry
from cStringIO import StringIO

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
