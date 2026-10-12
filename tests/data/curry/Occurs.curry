-- The programs of unit_occurs.py: the occurs check at the union of two
-- classes of free variables in a strict equality (the decision of
-- 2026-10-12 on the Fair Scheme).  A merged class with a member whose
-- generator instance contains another member has no finite instance, and
-- the constraint step fails.
module Occurs where

data N = Z | S N

isS :: N -> Bool
isS (S _) = True

unS :: N -> N
unS (S n) = n

isZ :: N -> Bool
isZ Z = True
isZ (S _) = False

-- The goal of the Lean counterexample: the equality cell e is shared
-- between the two alternatives of the choice.  The left alternative makes
-- the constraint cell x =:= y while both are free.  The right alternative
-- narrows x to S x', unites x' with y, and then meets the shared cell at
-- its root: the union of the class of x with the class {x', y} would put
-- x' inside the instance of its own class.  The step fails, and the value
-- is True alone (KiCS2 3.5.0: True and False).
k :: N -> N -> Bool -> Bool
k (S x') y e = (x' =:= y) &> (e &> False)

goal :: Bool
goal = let e = x =:= y in e ? k x y e  where x, y free

-- The right alternative alone.  The decision gives it no value.
goalR :: Bool
goalR = let e = x =:= y in k x y e  where x, y free

-- The second shape (the audit's Fsb.g10): x = J x1 with x1 ~ y, and
-- y = J y1 with y1 ~ x, a cycle through two classes.  The decision gives
-- it no value (KiCS2: True).
data R = N | J R

unJ :: R -> R
unJ (J r) = r

isJ :: R -> Bool
isJ (J _) = True

g10 :: Bool
g10 = (x =:= unJ y) &> (y =:= unJ x) &> True where x, y free

-- The shared cell with the second type: the right alternative unites the
-- leaf of x with y and then meets the cell.  True alone.
goalJ :: Bool
goalJ = let e = x =:= y in e ? ((unJ x =:= y) &> (e &> False)) where x, y free

-- The controls: unions without a cycle keep their values.

-- A narrowed variable united with a free one through a shared cell: the
-- class {x, y} is decided through x, and y reads its instance through the
-- class.  True twice: one value per alternative.
ctrlShared :: Bool
ctrlShared = let e = x =:= y in e ? (isS x &> e &> isS y) where x, y free

-- The instance of the merged class reaches another decided class without
-- a cycle: x = J x1, x1 ~ z, z = J z1.
ctrlChain :: Bool
ctrlChain = let e = x =:= y
            in e ? (isJ x &> (unJ x =:= z) &> isJ z &> e &> isJ y)
            where x, y, z free

-- A variable united with a leaf of another instance, then that instance
-- united with a third variable: no class holds a variable of its own
-- instance.
ctrlLeaf :: Bool
ctrlLeaf = let e = x =:= z
           in e ? (isS x &> (unS x =:= y) &> e &> isS z)
           where x, y, z free

-- Two narrowed variables united: their instances are paired leaf by leaf.
ctrlPair :: (Bool, Bool)
ctrlPair = isS x &> isS y &> (x =:= y) &> (isZ (unS x), isZ (unS y)) where x, y free

-- The five-cell goal of Constraints.curry (g16) keeps its values.
fiveCells :: (Bool, Bool, Bool, Bool, Bool)
fiveCells = (b =:= a) &> (c =:= d &> d =:= e) &> (not b, a =:= c, c, d, a) where a, b, c, d, e free
