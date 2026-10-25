-- The sharing benchmark's permutation sort of four computed primes.
-- Upstream BenchKiCS2 lists goal1, goal2 and goal3; goal3 includes both
-- prime generation and nondeterministic sorting.
module ShareNonDetBench where
import qualified ShareNonDet
main :: [Int]
main = ShareNonDet.goal3
