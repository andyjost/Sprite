-- Finite instances of the unchanged upstream examples/properties.
module TestDataListGoals where

import TestDataList
import Data.List

-- Source expectation: [1,2,3,4]
appendGoal = [1,2]++[3,4]

-- Source expectation: [1,3,2,4]
nubGoal = nub [1,3,1,2,3,2,4]

-- Source expectation: True
allGoal = all (<5) [1,2,3,4]

-- Source expectation: 4
lastGoal = lastSpec [1,2,3,4]

-- Source expectation: [1,2,3]
initGoal = initSpec [1,2,3,4]

