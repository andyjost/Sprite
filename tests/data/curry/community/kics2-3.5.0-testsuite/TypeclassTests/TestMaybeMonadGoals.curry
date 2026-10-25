-- Finite instances of the unchanged upstream examples/properties.
module TestMaybeMonadGoals where

import TestMaybeMonad

-- Source expectation: Nothing
checkTestDoMaybe1 = doMaybe1

-- Source expectation: Just (True,42)
checkTestDoMaybe2 = doMaybe2

