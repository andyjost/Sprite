-- Finite instances of the unchanged upstream examples/properties.
module TestDerivingGoals where

import TestDeriving

-- Source expectation: True
checkTestOrd1 = (Red < Blue)

-- Source expectation: True
checkTestOrd2 = (Leaf Red < Leaf Blue)

-- Source expectation: Red
readColor = read (show Red) :: Color

-- Source expectation: Leaf Red
readTree = read (show (Leaf Red)) :: Tree Color

