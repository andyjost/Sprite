import Control.SetFunctions
f = True ? False
goal1 = allValues (set0 f)
goal2 = allValues (set0 (True ? False))
main = (goal1, goal2) -- ([True, False], [True, False])
