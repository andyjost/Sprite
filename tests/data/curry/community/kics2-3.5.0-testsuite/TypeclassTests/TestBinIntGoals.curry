-- Finite instances of the unchanged upstream examples/properties.
module TestBinIntGoals where

import TestBinInt
import Prelude hiding (succ, pred)

-- Source expectation: 3 + Zero
checkTestZeroPlus3 = Zero + 3

-- Source expectation: 0
checkTestZeroMult3 = Zero * 3

-- Source expectation: ((1,2) ? (2,1) ? (-2,-1) ? (-1,-2))
checkTestNarrMultTwo = solutionOf (\ (x,y) -> x * y == (2::BinInt))


solutionOf :: Data a => (a -> Bool) -> a
solutionOf predicate = predicate x &> x where x free

-- Source property at a concrete finite argument: 2
signedAddition = ((-3) + 5 :: BinInt)

-- Source property at a concrete finite argument: -15
signedMultiplication = ((-3) * 5 :: BinInt)
