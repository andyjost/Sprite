-- Finite instances of the unchanged upstream examples/properties.
module TestInfiniteGoals where

import TestInfinite

-- Source expectation: [1,1,2,3,5,8,13,21,34,55]
checkTestFibs10 = take 10 fibs

-- Source expectation: [2,3,5,7,11]
checkTestPrimes5 = take 5 primes

-- Source expectation: [1,2,3,4,5,6,8,9,10,12]
checkTestHamming10 = take 10 hamming

