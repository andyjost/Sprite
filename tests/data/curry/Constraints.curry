-- The programs of unit_constraints.py: the equational constraints (=:=) and
-- (=:<=) over free variables, from the audit of the implementation against
-- the proved rules of the Fair Scheme (issues #127, #128 and #129).  The
-- names of the goals are those of the issues.
module Constraints where

-- Issue #127: a decided class whose union-find root has no generator.  The
-- class {a, b} (b decided by not b) is united into the class {c, d, e} by
-- the constraint a =:= c, and the union by size makes c the root, which has
-- no generator.  The yield of c reads the generator at the root.
g16b :: (Bool, Bool, Bool)
g16b = (b =:= a) &> (c =:= d &> d =:= e) &> (not b, a =:= c, c) where a, b, c, d, e free

g16 :: (Bool, Bool, Bool, Bool, Bool)
g16 = (b =:= a) &> (c =:= d &> d =:= e) &> (not b, a =:= c, c, d, a) where a, b, c, d, e free

-- The control: classes of equal size.
g14 :: (Bool, Bool, Bool)
g14 = (a =:= b) &> (not b, a =:= c, c) where a, b, c free

-- Issue #128: a merge of two classes bound to different terms.  In the
-- second alternative of g18, x reads B True and y reads B False through the
-- bindings of their leaves before the equality step, so the step fails.
data T = A | B Bool

inner :: T -> Bool
inner A = False
inner (B b) = b

isB :: T -> Bool
isB (B _) = True

g18 :: (T, T)
g18 = let e = x =:= y
      in (e &> isB x &> (A, A))
         ? (isB x &> isB y &> (inner x =:<= True) &> (inner y =:<= False) &> e &> (x, y))
      where x, y free

g18t :: Bool
g18t = let e = x =:= y
       in (e &> isB x &> False)
          ? (isB x &> isB y &> (inner x =:<= True) &> (inner y =:<= False) &> e &> True)
       where x, y free

-- The control: the direct merge of two bound classes.
g5 :: (Bool, Bool)
g5 = (x =:<= True) &> (y =:<= False) &> (x =:= y) &> (x, y) where x, y free

-- Two classes bound to equal terms in distinct cells: the merge keeps the
-- binding.
eqJust :: (Maybe Bool, Maybe Bool)
eqJust = (x =:<= Just True) &> (y =:<= Just True) &> (x =:= y) &> (x, y) where x, y free

-- Two classes bound to equal but unevaluated terms in distinct cells, united
-- by a constraint cell the first alternative shares.  The merge counts the
-- two cells as different and fails the step, so the second value (2, 2) is
-- lost; KiCS2 gives both values.  The rule is the owner's (Remark 2.70).
eqShapeG18 :: (Int, Int)
eqShapeG18 = let e = x =:= y
             in (e &> (0, 0)) ? ((x =:<= (1 + 1)) &> (y =:<= (1 + 1)) &> e &> (x, y))
             where x, y free

-- The binding of a class whose root changes at a union in which neither
-- id of the constraint is the old root: the binding moves to the new root.
orphan :: (Bool, Bool)
orphan = (x =:= y) &> (x =:<= True) &> (u =:= v) &> (v =:= w) &> (y =:= v) &> (x, u) where x, y, u, v, w free

-- Issue #129: a variable that another alternative narrowed is free in this
-- one.  In the second alternative of g20 the non-strict equality binds x to
-- failB without a step at the right side, and the yield is (True, True).
failB :: Bool
failB = failed

g20 :: (Bool, Bool)
g20 = (not x, x) ? ((x =:<= failB) &> (True, True)) where x free

-- The control: no generator before the binding.
g22 :: (Bool, Bool)
g22 = (x =:<= failB) &> (True, True) where x free

-- The yield form under =:= alone: the second alternative yields one
-- variable twice.
g15 :: (Bool, Bool)
g15 = (not x, x) ? ((x =:= y) &> (x, y)) where x, y free

-- A strict application of such a variable narrows it by the existing
-- generator, as before: the rule covers the equality steps alone.
strictApp :: Bool
strictApp = (not x && x) ? (id $! x) where x free
