import cytest # from ./lib; must be first
import curry, unittest

class CompleteTestCase(cytest.TestCase):
  @cytest.with_flags(backend='cxx', defaultconverter='topython')
  def test_complete(self):
    Loop = curry.compile(
      '''
      loop = loop
      main :: Int
      main = 1 ? loop ? 2
      '''
      )
    e = curry.eval(Loop.main)
    self.assertEqual(sorted([next(e), next(e)]), [1,2])

