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
