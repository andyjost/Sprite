'''Issue #141: forwarded successors keep their punctuation and context.'''
import cytest # from ./lib; must be first
from curry.expressions import fwd
import curry
import unittest

class TestForwardedPrinter(cytest.TestCase):
  def test_forwarded_successors(self):
    one = curry.raw_expr(fwd(1))
    two = curry.raw_expr(fwd(fwd(2)))
    for form, text in (((one, two), '(1, 2)'),
        ([one, two], '[1, 2]'), ((two, (one, two)), '(2, (1, 2))')):
      self.assertEqual(str(curry.raw_expr(form)), text)
    P = curry.import_('Prelude')
    self.assertEqual(str(curry.raw_expr([P.Just, two])), 'Just 2')

  def test_forwarded_spine(self):
    from curry.expressions import cons
    value = curry.raw_expr(cons(1, fwd([2, 3])))
    self.assertEqual(str(value), '[1, 2, 3]')

  def test_io_under_tuple(self):
    SF = curry.import_('Control.SetFunctions')
    goal = (SF.values2list(SF.set0(curry.choice(0, 1))), 5)
    value = next(curry.eval(goal, converter=None))
    self.assertEqual(str(value), '(IO [0, 1], 5)')

if __name__ == '__main__':
  unittest.main()
