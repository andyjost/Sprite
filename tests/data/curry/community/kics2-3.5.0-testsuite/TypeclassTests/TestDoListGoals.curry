-- Finite instances of the unchanged upstream examples/properties.
module TestDoListGoals where

import TestDoList

-- Source expectation: [42]
checkTestList42Comp = list42Comp

-- Source expectation: [42]
checkTestList42Do = list42Do

-- Source expectation: []
checkTestListEmptyComp = listEmptyComp

-- Source expectation: []
checkTestListEmptyDo = listEmptyDo

