-- Finite instances of the unchanged upstream examples/properties.
module TestNondetGoals where

import TestNondet

-- Source expectation: 0
checkCoinYields0 = coin

-- Source expectation: 1
checkCoinYields1 = coin

-- Source expectation: (1 ? 0)
checkTestCoinValues = coin

-- Source expectation: (0 ? 1 ? 2)
checkAddCoinCoin = (coin+coin)

-- Source expectation: (0 ? 1 ? 1 ? 2)
checkAddCoinCoinMulti = (coin+coin)

-- Source expectation: (0 ? 2)
checkDoubleCoin = (double coin)

-- Source expectation: [1,2,3,4]
checkTestSort1234 = (psort [4,1,3,2])

