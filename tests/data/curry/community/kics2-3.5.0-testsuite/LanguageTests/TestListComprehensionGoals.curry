-- Finite instances of the unchanged upstream examples/properties.
module TestListComprehensionGoals where

import TestListComprehension

-- Source expectation: [1,9,25,49,81,121,169,225,289,361]
checkTestSquareOdds = [ x*x | x <- [1..20], odd x ]

-- Source expectation: [(1,2),(1,3),(1,4),(2,3),(2,4),(3,2),(3,4)]
checkTestPairs = [ (i,j) | i <- [1..3], j <- [2..4], i /= j ]

-- Source expectation: [1,2,6,24,120,720,5040,40320,362880,3628800]
checkTestFacs = take 10 (map (foldr (*) 1) [ [1..n] | n <- [1..] ])

-- Source expectation: [(1,2,3),(1,3,4),(1,4,5),(1,5,6),(1,6,7),(2,3,5),(2,4,6),(2,5,7),(2,6,8) ,(3,2,5),(3,4,7),(3,5,8),(3,6,9),(4,2,6),(4,3,7),(4,5,9),(4,6,10)]
checkTestLetComp = [ (x,y,z) | x <- [1 .. 4], y <- [2 .. 6], let z = x+y, x /= y ]

