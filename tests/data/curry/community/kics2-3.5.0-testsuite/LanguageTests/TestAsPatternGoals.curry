-- Finite instances of the unchanged upstream examples/properties.
module TestAsPatternGoals where

import TestAsPattern

-- Source expectation: [1,1,2]
checkTestSimple = (f1 [1,2])

-- Source expectation: [1,1,1,2]
checkTestNonLinearAs1 = (g1 [1,2] [1,2])

-- Source expectation: no values
checkTestNonLinearAs2 = (g1 [1,2] [3,4])

-- Source expectation: [(3,13)]
checkTestFuncPatAs1 = (h1 (zip [1..9] [11..19]))

-- Source expectation: ([[(2,3),(42,99)]],[(42,99)])
checkTestFuncPatAs2 = (h2 [[(1,2)],[(2,3),(42,99)],[]])

-- Source expectation: no values
checkTestFuncPatAs3 = (h3 [1,2,3,4])

