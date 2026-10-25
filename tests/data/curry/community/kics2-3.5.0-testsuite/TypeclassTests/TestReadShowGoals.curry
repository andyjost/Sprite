-- Finite instances of the unchanged upstream examples/properties.
module TestReadShowGoals where

import TestReadShow

-- Source expectation: True
readBool = read (show True) :: Bool

-- Source expectation: -42
readInt = read (show (-42 :: Int)) :: Int

-- Source expectation: "Curry"
readString = read (show "Curry") :: String

-- Source expectation: Just 42
readMaybe = read (show (Just (42 :: Int))) :: Maybe Int

-- Source expectation: (42,True)
readPair = read (show ((42 :: Int),True)) :: (Int,Bool)

