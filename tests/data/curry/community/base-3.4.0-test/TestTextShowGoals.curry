-- Finite instances of the unchanged upstream examples/properties.
module TestTextShowGoals where

import TestTextShow
import Prelude hiding (ShowS, showString)
import Text.Show

-- Source expectation: "Curry"
stringGoal = showString "Curry" []

-- Source expectation: "Curry"
concatGoal = (showString "Cur" . showString "ry") []

-- Source expectation: "ababab"
replicateGoal = replicateS 3 (showString "ab") []

-- Source expectation: "Curry"
concatList = concatS (map showString ["Cur","ry"]) []

