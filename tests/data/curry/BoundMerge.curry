-- The programs of unit_boundmerge.py: the merge of two bound classes at a
-- union of the constraint step (decision D26 of 2026-10-12).  A strict
-- equality x =:= y of two free variables makes a constraint cell, which the
-- two alternatives of ? share.  The first alternative unites the two
-- classes while they are unbound.  The second binds them, or their leaves,
-- by =:<= and then meets the cell: the union merges two bound classes.
-- The merged class keeps one binding, and the strict equality of the two
-- bindings guards the result of the step: the alternative has its value
-- when the two bindings are equal and none when they differ.
--
-- A binding not yet evaluated is a sum, 1 + 1, as in eqShapeG18: the
-- translation to ICurry folds not False and ident True to True, and a
-- literal constructor is one static cell in the C++ backend, so two
-- occurrences of True are one cell there and make no guard.
module BoundMerge where

data T = A | B Int

inner :: T -> Int
inner A = 0
inner (B n) = n

isB :: T -> Bool
isB (B _) = True

data P = N | P Int Int

isP :: P -> Bool
isP (P _ _) = True

leaf1 :: P -> Int
leaf1 (P a _) = a

leaf2 :: P -> Int
leaf2 (P _ b) = b

-- Two bindings already evaluated and equal, in distinct cells: the guard
-- Just True =:= Just True succeeds at once.
evalEq :: (Maybe Bool, Maybe Bool)
evalEq = let e = x =:= y
         in (e &> (Nothing, Nothing))
            ? ((x =:<= Just True) &> (y =:<= Just True) &> e &> (x, y))
         where x, y free

-- Two equal bindings not yet evaluated (the shape of eqShapeG18 of
-- Constraints.curry): the guard evaluates both.
unevalEq :: (Int, Int)
unevalEq = let e = x =:= y
           in (e &> (0, 0)) ? ((x =:<= (1 + 1)) &> (y =:<= (1 + 1)) &> e &> (x, y))
           where x, y free

-- Two different values: the guard fails, and the alternative has no value.
diffVal :: (Int, Int)
diffVal = let e = x =:= y
          in (e &> (0, 0)) ? ((x =:<= (1 + 1)) &> (y =:<= (1 + 2)) &> e &> (x, y))
          where x, y free

-- One cell bound to both classes: one binding, no guard.
sameCell :: (Int, Int)
sameCell = let e = x =:= y
               b = 1 + 1
           in (e &> (0, 0)) ? ((x =:<= b) &> (y =:<= b) &> e &> (x, y))
           where x, y free

-- Bound leaf classes under constructors (the shape of g18): the pairing of
-- the two generators unites the leaf classes, both bound, with equal
-- leaves and with different leaves.
leafEq :: (T, T)
leafEq = let e = x =:= y
         in (e &> isB x &> (A, A))
            ? (isB x &> isB y &> (inner x =:<= (1 + 1)) &> (inner y =:<= (1 + 1)) &> e &> (x, y))
         where x, y free

leafDiff :: (T, T)
leafDiff = let e = x =:= y
           in (e &> isB x &> (A, A))
              ? (isB x &> isB y &> (inner x =:<= (1 + 1)) &> (inner y =:<= (1 + 2)) &> e &> (x, y))
           where x, y free

-- Three bound classes united at one step: the classes of the leaves are
-- {x1}, {x2, y1} and {y2}, each bound; the pairing of x = P x1 x2 with
-- y = P y1 y2 unites the three, with two guards.
three :: (P, P)
three = let e = x =:= y
        in (e &> isP x &> (N, N))
           ? (isP x &> isP y &> (leaf2 x =:= leaf1 y)
              &> (leaf1 x =:<= (1 + 1)) &> (leaf2 x =:<= (1 + 1))
              &> (leaf2 y =:<= (1 + 1)) &> e &> (x, y))
        where x, y free

threeDiff :: (P, P)
threeDiff = let e = x =:= y
            in (e &> isP x &> (N, N))
               ? (isP x &> isP y &> (leaf2 x =:= leaf1 y)
                  &> (leaf1 x =:<= (1 + 1)) &> (leaf2 x =:<= (1 + 1))
                  &> (leaf2 y =:<= (1 + 2)) &> e &> (x, y))
            where x, y free

-- A guard whose evaluation narrows a free variable inside the bindings:
-- Just z =:= Just True narrows z.
narrowIn :: (Maybe Bool, Maybe Bool, Bool)
narrowIn = let e = x =:= y
           in (e &> (Nothing, Nothing, False))
              ? ((x =:<= Just z) &> (y =:<= Just True) &> e &> (x, y, z))
           where x, y, z free

-- A guard whose evaluation narrows a free variable under a constructor
-- of the bindings: B z =:= B (1 + 1) binds z.
narrowLeaf :: (T, T, Int)
narrowLeaf = let e = x =:= y
             in (e &> (A, A, 0))
                ? ((x =:<= B z) &> (y =:<= B (1 + 1)) &> e &> (x, y, z))
             where x, y, z free
