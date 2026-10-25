-- Finite instances of the unchanged upstream examples/properties.
module TestFCaseGoals where

import TestFCase

-- Source expectation: True
checkTestNot1 = (fNot False)

-- Source expectation: (True ? False)
checkTestNot2 = (fNot _)

-- Source expectation: (True ? False)
checkTestABool1 = aBool1

-- Source expectation: (True ? False)
checkTestABool2 = aBool2

-- Source expectation: (1 ? 2)
checkTestFirstOrSecond = (firstOrSecond [1,2,3])

-- Source expectation: 2
checkTestPosFirstOrSecond = (posFirstOrSecond [0,2,3])

