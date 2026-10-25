------------------------------------------------------------------------------
--- Some tests for library `Data.Function`
---
--- To run all tests automatically by CurryCheck, use the command:
---
---     > curry-check TestDataFunction
------------------------------------------------------------------------------

import Data.Function
import Data.List     ( sortBy )
import Test.Prop

fac :: Int -> Int
fac n = foldr (*) 1 [1 .. n]

facFix :: Int -> Int
facFix = fix (\f n -> if n<=0 then 1 else n * f (n - 1))

fixFacCorrect :: Prop
fixFacCorrect = fac <=> facFix

testTimesOnInc :: Int -> Int -> Prop
testTimesOnInc x y = ((*) `on` (+1)) x y -=- (x+1) * (y+1)

testSortOnFst :: Bool -> Prop
testSortOnFst x =
  snd (head (sortBy ((<=) `on` fst) [(2,id), (1, not)])) x -=- not x


testOnMult :: (a -> Int) -> a -> a -> Prop
testOnMult f x y = ((*) `on` f) x y -=- f x * f y

testOnAdd1 :: Ordering -> Ordering -> Prop
testOnAdd1 x y = ((+) `on` f) x y -=- f x + f y
 where f = fromEnum

testOnAdd2 :: Int -> Int -> Prop
testOnAdd2 x y = ((+) `on` f) x y -=- f x + f y
 where f = \n -> n*n
