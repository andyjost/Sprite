-- Nullary expressions from the properties/examples in TestMPTCCoerce.curry.
module TestMPTCCoerceGoals where

import TestMPTCCoerce

-- Source states: 1
boolToInt = (coerce True :: Int)

-- Source states: True
intToBool = (coerce (1::Int) :: Bool)

-- Source states: False
composeFalse = (compCoerce False :: Bool)

-- Source states: True
composeTrue = (compCoerce True :: Bool)
