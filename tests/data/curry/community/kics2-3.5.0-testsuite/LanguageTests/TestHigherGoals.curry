-- Finite instances of the unchanged upstream examples/properties.
module TestHigherGoals where

import TestHigher

-- Source expectation: [1,3,2]
checkTestMapInc = (map inc [0,2,1])

-- Source expectation: [1,3,2]
checkTestMapPlus1 = (map (+ 1) [0,2,1])

-- Source expectation: 3
checkTestFoldrPlus = (foldr (+) 0 [1,0,2])

-- Source expectation: 120
checkTestFoldrMult = (foldr (*) 1 [1,2,3,4,5])

-- Source expectation: 120
checkTestFoldrLambda = (foldr (\ x y -> x * y) 1 [1,2,3,4,5])

