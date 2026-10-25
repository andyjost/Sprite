module LiftGuardB1 where
import Control.SetFunctions

data One = One deriving (Eq, Ord)

good2 :: Bool
good2 = ((x :: One) =:= One) &> ((x =:= y) &> True) where x,y free

inside2 :: [Bool]
inside2 = sortValues (set1 (\a -> a &> failed) good2)

plain2 :: [Bool]
plain2 = sortValues (set1 id good2)
