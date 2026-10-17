'''Issue #155: one class for a choice inside an I/O action.'''
import cytest # from ./lib; must be first
import curry
import unittest

class TestNondetIO(cytest.TestCase):
  def test_both_routes(self):
    P = curry.import_('Prelude')
    for goal in (P.print(curry.choice(1, 2)), curry.parse('print (1 ? 2)')):
      with self.assertRaises(curry.NondetError) as caught:
        next(curry.eval(goal))
      self.assertIs(type(caught.exception), curry.NondetError)
      self.assertEqual(str(caught.exception), 'non-determinism in monadic actions occurred!')

  def test_explicit_nondet_ioerror(self):
    P = curry.import_('Prelude')
    with self.assertRaises(curry.NondetError) as caught:
      next(curry.eval(P.ioError(P.NondetError('explicit'))))
    self.assertEqual(str(caught.exception), 'nondet error: explicit')

  def test_catch_preserves_nondet_constructor(self):
    goal = curry.parse('catch (print ((1 ? 2) :: Int) >> return "") (\\e -> return (show e)) :: IO String')
    self.assertEqual(curry.eval(goal).one(),
        'nondet error: non-determinism in monadic actions occurred!')

if __name__ == '__main__':
  unittest.main()
