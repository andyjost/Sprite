-- Finite instances of the unchanged upstream examples/properties.
module TestNarrowingGoals where

import TestNarrowing

-- Source expectation: S (S O)
checkTestAdd = (add (S O) (S O))

-- Source expectation: S O
checkTestDiff = solutionOf (\x -> add x (S O) =:= S (S O))

-- Source expectation: S O
checkTestSub = (sub (S (S O)) (S O))

-- Source expectation: (O ? S O ? S (S O))
checkTestLeq = solutionOf (\x -> leq x (S(S O)))

-- Source expectation: 4
checkTestLast1234 = last [1,2,3,4]


solutionOf :: Data a => (a -> Bool) -> a
solutionOf predicate = predicate x &> x where x free
