-- Finite instances of the unchanged upstream examples/properties.
module TestClassInstGoals where

import TestClassInst

-- Source expectation: (1?0)
checkTestChoiceInt = (choice :: Int)

-- Source expectation: ([0,0]?[0,1]?[1,0]?[1,1])
checkTestTwoChoices = ([choice,choice] :: [Int])


-- Source property at a concrete finite argument: 42
dupInt = dup (21::Int)

-- Source property at a concrete finite argument: True
dupBool = dup True
