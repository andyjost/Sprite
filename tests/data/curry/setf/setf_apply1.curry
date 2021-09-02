import Control.SetFunctions

-- PACKS, KiCS2 both return [True,False]
f x = x
a = True ? False
goal0 = sortValues $ set1 (\x -> x a) f

-- PACKS, KiCS2 both return [True,False]
g x = x ? not x
goal1 = sortValues $ set1 (\x -> x True) g

-- PACKS, KiCS2 both return [True,False,False,True]
goal2 = sortValues $ set1 (\x -> x a) g
