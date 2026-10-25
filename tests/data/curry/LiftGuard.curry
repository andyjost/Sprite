module LiftGuard where
import Control.SetFunctions

data T = T T

cyc :: Bool
cyc = (x =:= T x) &> True where x free

goal0 :: [Bool]
goal0 = sortValues (set1 id failed)

goal1 :: [Bool]
goal1 = sortValues (set1 id cyc)

goal2 :: [Bool]
goal2 = sortValues (set1 (\a -> a ? True) cyc)

nested1 :: [[Bool]]
nested1 = sortValues (set1 id goal1)

nested2 :: [[Bool]]
nested2 = sortValues (set1 id goal2)

data One = One deriving (Eq, Ord)

one :: [One]
one = sortValues (set1 (\a -> a ? One) x) where x free

good :: Bool
good = ((x :: One) =:= y) &> True where x,y free

inside :: [Bool]
inside = sortValues (set1 (\a -> a &> failed) good)

programChoice :: [Bool]
programChoice = sortValues (set1 (\a -> a ? True) (True ? failed))

onlyOne :: One -> Bool
onlyOne One = True

oneBinding :: ([Bool],One)
oneBinding = (sortValues (set1 onlyOne x),x) where x free
