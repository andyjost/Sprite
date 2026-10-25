module TestSearchSetFunctionsGoals where
import TestSetFunctions
import Control.Search.SetFunctions
main = sortValues (set1 f bigCoin)
goal0 = shortestItin Portland Hamburg
goal1 = shortestItinSelect Portland Hamburg
goal2 = queens 4
goal3 = queens 6
