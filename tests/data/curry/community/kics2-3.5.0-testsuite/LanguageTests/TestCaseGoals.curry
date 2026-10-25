-- Finite instances of the unchanged upstream examples/properties.
module TestCaseGoals where

import TestCase

-- Source expectation: []
checkTestSwap1 = (swap [] )

-- Source expectation: [1]
checkTestSwap2 = (swap [1] )

-- Source expectation: [2,1]
checkTestSwap3 = (swap [1,2] )

-- Source expectation: [1,2,3]
checkTestSwap4 = (swap [1,2,3])

-- Source expectation: 0
checkTestf1 = (f [] )

-- Source expectation: no values
checkTestf2 = (f [1])

-- Source expectation: 152
checkTestf3 = (f [1,2])

-- Source expectation: True
checkTestg1 = (g (Just "xyz"))

-- Source expectation: False
checkTestg2 = (g (Just "ab") )

-- Source expectation: True
checkTesth1 = (h [1,2])

-- Source expectation: False
checkTesth2 = (h [1,3])

-- Source expectation: False
checkTesth3 = (h [2,div 1 0])

-- Source expectation: 1
checkTestFirstOrSecond = (firstOrSecond [1,2,3])

-- Source expectation: 2
checkTestPosFirstOrSecond = (posFirstOrSecond [0,2,3])

