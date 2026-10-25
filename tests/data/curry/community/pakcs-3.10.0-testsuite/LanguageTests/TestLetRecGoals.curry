-- Nullary expressions from the properties/examples in TestLetRec.curry.
module TestLetRecGoals where

import TestLetRec

-- Source states: [1,1,1,1,1]
ones = ones5

-- Source states: [2,2,2,2,2]
twos = twolist 5

-- Source states: [1,2,1,2,1,2]
oneTwo = onetwo 6
