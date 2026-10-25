------------------------------------------------------------------------------
--- Some tests for library `Data.Function`
---
--- To run all tests automatically by CurryCheck, use the command:
---
---     > curry-check TestFunction
------------------------------------------------------------------------------

import Data.Function
import Test.Prop

testOnMult :: (a -> Int) -> a -> a -> Prop
testOnMult f x y = ((*) `on` f) x y -=- f x * f y

testOnAdd1 :: Ordering -> Ordering -> Prop
testOnAdd1 x y = ((+) `on` f) x y -=- f x + f y
 where f = fromEnum

testOnAdd2 :: Int -> Int -> Prop
testOnAdd2 x y = ((+) `on` f) x y -=- f x + f y
 where f = \n -> n*n
