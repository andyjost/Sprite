-- Nullary expressions from the properties/examples in TestNewtype.curry.
module TestNewtypeGoals where

import TestNewtype

-- Source states: 42
nonStrict = headIfTrue failed False

-- Source states: "LIST [1,2]"
shownList = show (LIST [1,2::Int])

-- Source states: True
readShow = (read ("LIST " ++ show [1,2::Int]) :: LIST Int) == LIST [1,2]

-- Source states: (False,False)
doubleFalse = runXD False

-- Source states: (True,True)
doubleTrue = runXD True
