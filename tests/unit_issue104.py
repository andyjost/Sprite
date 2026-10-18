'''Issue #104: a symbol at the head of a Python list is a list element.'''
import cytest # from ./lib; must be first
import curry
import unittest

SOURCE = r'''
data Nat = O deriving (Eq, Show)
inc, dbl :: Int -> Int
inc x = x + 1
dbl x = x * 2
zero, anotherZero :: Int
zero = 0
anotherZero = 0
applyAll :: [Int -> Int] -> Int -> [Int]
applyAll fs x = map (\f -> f x) fs
'''


class TestIssue104(cytest.TestCase):
  def test_list_of_functions(self):
    M = curry.compile(SOURCE)
    functions = curry.term([M.inc, M.dbl])
    self.assertEqual(curry.typeof(functions), '[Int -> Int]')
    self.assertEqual(str(functions), '[inc,dbl]')
    self.assertEqual(curry.eval(M.applyAll(functions, 5)).one(), [6, 10])
    self.assertEqual([curry.eval(f(5)).one() for f in curry.eval(functions).one()], [6, 10])

  def test_list_of_nullary_constructors_and_functions(self):
    M = curry.compile(SOURCE)
    self.assertEqual(str(curry.term([M.O, M.O])), '[O,O]')
    self.assertEqual(curry.eval([M.O, M.O]).one(), [M.O, M.O])
    self.assertEqual(curry.eval([M.zero, M.anotherZero]).one(), [0, 0])


if __name__ == '__main__':
  unittest.main()
