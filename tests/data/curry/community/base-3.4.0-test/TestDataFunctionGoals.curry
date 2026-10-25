-- Finite instances of the unchanged upstream examples/properties.
module TestDataFunctionGoals where

import TestDataFunction
import Data.Function
import Data.List (sortBy)

-- Source expectation: 720 (fac <=> facFix instantiated at 6)
factorial = facFix 6

-- Source expectation: 12
onIncrement = ((*) `on` (+1)) (2::Int) 3

-- Source expectation: True
sortOnFirst = snd (head (sortBy ((<=) `on` fst) [(2,id),(1,not)])) False

