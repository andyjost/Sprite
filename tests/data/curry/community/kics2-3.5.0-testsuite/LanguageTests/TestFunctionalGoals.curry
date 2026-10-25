-- Finite instances of the unchanged upstream examples/properties.
module TestFunctionalGoals where

import TestFunctional

-- Source expectation: [1,2,3,4]
checkTestAppend1234 = append [1,2] [3,4]

-- Source expectation: [4,3,2,1]
checkTestRev1234 = rev [1,2,3,4]

