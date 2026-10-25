-- Finite instances of the unchanged upstream examples/properties.
module TestNatGoals where

import TestNat

-- Source expectation: 3 + Zero
checkTestZeroPlus3 = Zero + 3

-- Source expectation: 0
checkTestZeroMult3 = Zero * 3

-- Source expectation: True
checkTestElem1 = elem (Succ Zero) [Zero, 1, 42]

-- Source expectation: True
checkTestElem42 = elem 42 [Zero, 1, 42]


-- Source property at a concrete finite argument: Zero
multiplyAny = Zero * (42::Nat)
