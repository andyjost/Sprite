-- Nullary expressions from the properties/examples in TestFuncPattern.curry.
module TestFuncPatternGoals where

import TestFuncPattern
import Data.Maybe (isJust)

-- Source states: 201
last1 = TestFuncPattern.last (map (+1) [1..200])

-- Source states: 1
last2 = TestFuncPattern.last (take 10000 (repeat failed) ++ [1])

-- Source states: True
palindrome = pali "otto"

-- Source states: no values
notPalindrome = pali "toto"

-- Source states: Var "x"
simplified = simplify (Mul (Lit 1) (Var "x"))

-- Source states: True
justZeroGoal = isJust justZero

-- Source states: no values
justFailedGoal = isJust justFailed

-- Source states: True
pair00 = pair (O,O)

-- Source states: no values
pair01 = pair (O,S O)

-- Source states: no values
pairFailed = pair (O,failed)

-- Source states: True
nonlinearUnused = f (O,failed)

-- Source states: no values
nonlinearUsed = h (O,failed)

-- Source states: no values
failingPatternGoal = failingPattern (unknown :: [Int])

-- testVars1 checks the set; testVars2 checks the multiset of 256 copies.
variables = varInExp bigexp

-- Source states: [Red,Red,White,White,White,Blue,Blue]
dutchFlag = TestFuncPattern.solve [White,Red,White,Blue,Red,Blue,White]
