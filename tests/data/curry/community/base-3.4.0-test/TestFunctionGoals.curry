-- Finite instances of the unchanged upstream examples/properties.
module TestFunctionGoals where

import TestFunction
import Data.Function

-- Source expectation: 12
multiplyOn = ((*) `on` (\x -> x+1)) (2::Int) 3

-- Source expectation: 2
addEnum = ((+) `on` fromEnum) LT GT

-- Source expectation: 13
addSquare = ((+) `on` (\n -> n*n)) (2::Int) 3

