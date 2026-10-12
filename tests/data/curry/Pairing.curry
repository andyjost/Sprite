-- The programs of unit_pairing.py: the strict equality of a decided
-- variable and a variable that is free in the configuration records the
-- pair of the two variables (decision D25 of 2026-10-12) instead of
-- narrowing the free one against the instance of the decided one.  The
-- values are those of the narrowing reading, the forks are fewer, and a
-- cyclic pair fails the step through the occurs check of the union.
module Pairing where

data N = Z | S N

isS :: N -> Bool
isS (S _) = True

isZ :: N -> Bool
isZ Z = True
isZ (S _) = False

unS :: N -> N
unS (S n) = n

-- The equality cell holds the two variables; x is narrowed first through
-- another cell.
f :: N -> N -> N
f x y = (x =:= y) &> x

-- x decided to S x', y free: S _a, one value.
leftDecided :: N
leftDecided = isS x &> f x y where x, y free

-- The decided side on the right: S _a.
rightDecided :: N
rightDecided = isS y &> f x y where x, y free

-- Both branches of x: a value per decided branch, Z and S _a.
bothBranches :: N
bothBranches = (isZ x ? isS x) &> f x y where x, y free

-- The free variable reads the instance through the merged class.
readThrough :: (N, Bool)
readThrough = isS x &> (x =:= y) &> (y, isS y) where x, y free

-- The inner variable is narrowed after the union: (S Z, S Z).
deeper :: (N, N)
deeper = isS x &> (x =:= y) &> isZ (unS y) &> (x, y) where x, y free

-- Two decided variables are expanded, as before, and their leaves are
-- paired: (S Z, S Z).
bothDecided :: (N, N)
bothDecided = isS x &> isS y &> (x =:= y) &> isZ (unS x) &> (x, y)
  where x, y free

-- A free variable against a constructor term narrows as before: the term
-- is not the instance of a decided variable.  (S Z, Z).
againstTerm :: (N, N)
againstTerm = (x =:= S y) &> isZ y &> (x, y) where x, y free

-- A decided variable against a constructor term is expanded, as before:
-- S Z.
decidedAgainstTerm :: N
decidedAgainstTerm = isS x &> (x =:= S Z) &> x where x free

-- The cycle in the paired form: x decided to S x', x' united with y, then
-- x =:= y.  The pair {x, y} merges the class of x with {x', y}, and the
-- occurs check fails the step: no value.  The narrowing of y against S x'
-- ran without end here.
cycleVar :: Bool
cycleVar = isS x &> (unS x =:= y) &> (x =:= y) &> True where x, y free

-- The cycle through the matched argument: after the case on x, the body
-- reads x as the constructor cell S x' of the decided branch, a
-- constructor term to the step, which narrows y against it by a fork.
-- The equality below it, x' =:= y', meets the two variables: x' is
-- decided through its class with y, y' is free, and the pair fails the
-- occurs check.  No value, one fork later than cycleVar.
kLeaf :: N -> N -> Bool
kLeaf x@(S x') y = (x' =:= y) &> (x =:= y) &> True

cycleLeaf :: Bool
cycleLeaf = kLeaf x y where x, y free
