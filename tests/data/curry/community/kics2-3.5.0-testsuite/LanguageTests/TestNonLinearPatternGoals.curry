-- Finite instances of the unchanged upstream examples/properties.
module TestNonLinearPatternGoals where

import TestNonLinearPattern

-- Source expectation: no values
checkTestNonLinearSimple1 = (fstEqu [1,2] [2,3])

-- Source expectation: [2]
checkTestNonLinearSimple2 = (fstEqu [1,2] [1,3])

-- Source expectation: no values
checkTestNonLinearFirst = (f [1] [2])

-- Source expectation: (1 ? 2 ? 3)
checkTestMember = solutionOf (\x -> member x [1,2,3])


solutionOf :: Data a => (a -> Bool) -> a
solutionOf predicate = predicate x &> x where x free
