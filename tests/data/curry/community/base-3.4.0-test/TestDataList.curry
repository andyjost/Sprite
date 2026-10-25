------------------------------------------------------------------------------
--- Some tests for library `Data.List`
---
--- To run all tests automatically by CurryCheck, use the command:
---
---     > curry-check TestDataList
------------------------------------------------------------------------------

import Data.List
import Test.Prop

-- Now we can test properties of our program:

testAppend = ([1,2]++[3,4]) -=- [1,2,3,4]


testNub = (nub [1,3,1,2,3,2,4]) -=- [1,3,2,4]

nubNub :: Eq a => [a] -> [a]
nubNub = nub . nub

propNub = nubNub <=> (nub :: [Int] -> [Int])


testAll = always (all (<5) [1,2,3,4])


-- Specification of `last`:
lastSpec :: Data a => [a] -> a
lastSpec (_ ++ [x]) = x

lastCorrect :: Prop
lastCorrect = last <=> (lastSpec :: [Int] -> Int)


-- Specification of `init` (which is slightly more strict):
initSpec :: Data a => [a] -> [a]
initSpec (xs ++ [_]) = xs

initGroundCorrect :: [Int] -> Prop
initGroundCorrect xs = init xs <~> initSpec xs


propDelete :: Int -> [Int] -> Prop
propDelete x xs = x `notElem` xs ==> delete x xs -=- xs

propUnion1 :: Int -> [Int] -> Prop
propUnion1 x xs = always (x `elem` union xs [x])

propUnion2 :: Int -> [Int] -> [Int] -> Prop
propUnion2 x xs ys = x `elem` union xs ys -=- x `elem` xs || x `elem` ys

propIntersect :: Int -> [Int] -> [Int] -> Prop
propIntersect x xs ys = x `elem` intersect xs ys -=- x `elem` xs && x `elem` ys

propPermutations :: [Int] -> Prop
propPermutations xs = length (permutations xs) -=- foldr (*) 1 [1 .. length xs]
