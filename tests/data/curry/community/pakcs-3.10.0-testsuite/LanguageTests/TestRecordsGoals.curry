-- Nullary expressions from the properties/examples in TestRecords.curry.
module TestRecordsGoals where

import TestRecords

-- Source states: True
nameEq = name john1 == name john2

-- Source states: True
recordsEq = john1 == john2

-- Source states: True
recordsNeq = john1 /= john3

-- Source states: True
update = john1 {age=50} == john3

-- Source states: True
john = isJohn john1

-- Source states: True
bill = not (isJohn (john1 {name="Bill"}))
