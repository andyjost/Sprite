'''Non-linear functional patterns, independent of the community corpus.'''
import cytest # from ./lib; must be first


PAIR_PATTERN = '''
{-# LANGUAGE FunctionalPatterns #-}
import Data.Maybe
mkSamePair :: a -> (a,a)
mkSamePair x = (x,x)
fpair :: Data a => (a,a) -> a
fpair (mkSamePair x) = x
gpair :: Data a => (a,a) -> b -> b
gpair (mkSamePair x) y = y
justZero :: Maybe Int
justZero = let y,z free in fpair (y, gpair (y, Just 0) z)
justFailed :: Maybe Int
justFailed = let y,z free in fpair (y, gpair (y, Just failed) z)
zero = isJust justZero
bad = isJust justFailed
nested = let x free in (Just x,x) =:<= (Just (failed :: Int), failed)
linear = let x free in Just x =:<= Just (failed :: Int)
'''

LIFTED_PATTERN = '''
{-# LANGUAGE FunctionalPatterns #-}
f3 x = g3 x x &> x
g3 x (h3 x y) = success
  where z = y :: Int
h3 x y = x
main3 = f3 z where z free
f2 x = g2 x x &> x
g2 x1 z = h3 x2 (y :: Int) =:<= z &> x1 =:= x2 &> success
  where x2, y free
main2 = f2 z where z free
plain = let x,z free in (x,x) =:<= (z,z :: Bool)
opaque = let x,z free in (h3 x (0 :: Int),x) =:<= (z,z :: Bool)
'''


class TestNonlinearPatterns(cytest.TestCase):
  def check_program(self, source, expected):
    for mode in ('off', 'all'):
      with self.subTest(interpret=mode):
        code = '''
import cytest, curry
curry.reset(interpret=%r)
module = curry.compile(%r)
for goal, expected in %r:
  actual = [curry.show(value) for value in curry.eval(getattr(module, goal))]
  assert actual == expected, (goal, actual, expected)
  print(goal, actual)
''' % (mode, source, expected)
        proc = cytest.run_in_subprocess(code, timeout=90, address_space=2 << 30)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

  def test_repeated_pair_variable(self):
    self.check_program(PAIR_PATTERN, [
        ('zero', ['True']), ('bad', []), ('nested', []), ('linear', ['True'])])

  def test_lifted_repeated_variable(self):
    self.check_program(LIFTED_PATTERN, [
        ('main3', []), ('main2', ['_a']), ('plain', ['True']), ('opaque', [])])
