module Arithmetic where

import Test.Prop

addition :: Prop
addition = (1 + 2 :: Int) -=- 3
