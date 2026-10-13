-- The programs of unit_setfunctions_failures.py: the failure rule F2 of
-- the set functions in its deferred form (Definition 2.94 of the note on
-- the Fair Scheme; the owner's decision of 2026-10-12), Sprite's one rule
-- on both backends.  A failure that comes from an argument (a boxed
-- failure) drops the configuration that met it, as every failure does, and
-- the capsule records it; the capsule becomes a failure when its queue
-- empties with no value, no inside failure and some outside failure, and
-- its set stands otherwise.  The values in the comments are those of KiCS2
-- 3.5.0, observed through the harness of the Fair Scheme proofs.  The
-- probe modules of the audit of 2026-10-12 define the goals.
module SetFunctionsFailures where
import Control.SetFunctions

-- t1: the example of Christiansen, Hanus, Reck and Seidel (PPDP 2013): the
-- alternative a meets the failure of the argument and is dropped, the
-- alternative True stays.  [True]
t1 :: [Bool]
t1 = sortValues (set1 (\a -> a ? True) failed)

-- t2: the alternatives swapped.  [True]
t2 :: [Bool]
t2 = sortValues (set1 (\a -> True ? a) failed)

-- t3, t4: isEmpty of the two orders.  False, False.  isEmpty returns as
-- soon as one value exists, and the two orders must agree.
t3 :: Bool
t3 = isEmpty (set1 (\a -> a ? True) failed)

t4 :: Bool
t4 = isEmpty (set1 (\a -> True ? a) failed)

-- d2a, d2b: an inside failure beside the outside one, in both orders: the
-- set is empty.  True, True.
d2a :: Bool
d2a = isEmpty (set1 (\a -> a ? failed) failed)

d2b :: Bool
d2b = isEmpty (set1 (\a -> failed ? a) failed)

-- lazyT: a value produced before the failing argument is demanded.  [True]
lazyT :: [Bool]
lazyT = sortValues (set1 (\a -> True ? a) failed)

-- valThenFail: a value beside an outside failure that a later alternative
-- demands through an arithmetic step.  [1]
g :: Int -> Int
g a = 1 ? (a + 1)

valThenFail :: [Int]
valThenFail = sortValues (set1 g failed)

-- level, levelB: the level of a failure through two capsules.  The inner
-- capsule records the failure of the outer argument (it entered the chain
-- at the outer capsule) and the failure of its own argument; the records
-- at the innermost level decide (rule (d3)), so the inner capsule is a
-- plain failure, an inside failure of the outer function: [].  The two
-- orders of the alternatives of h must agree.
h :: Bool -> Bool -> Bool
h a b = a ? b

g2 :: Bool -> [Bool]
g2 a = sortValues (set2 h a failed)

level :: [[Bool]]
level = sortValues (set1 g2 failed)

hB :: Bool -> Bool -> Bool
hB a b = b ? a

g2B :: Bool -> [Bool]
g2B a = sortValues (set2 hB a failed)

levelB :: [[Bool]]
levelB = sortValues (set1 g2B failed)

-- levelC: the outer argument alone fails, demanded inside the inner
-- capsule: the inner capsule fails under the guard of the outer set, and
-- the outer capsule fails in turn.  No value.
g2C :: Bool -> [Bool]
g2C a = sortValues (set1 (\b -> a) True)

levelC :: [[Bool]]
levelC = sortValues (set1 g2C failed)

-- level2: the inner capsule fails for its own argument inside an outer
-- capsule whose argument is total: an inside failure of the outer
-- function.  [[]]
g3 :: Bool -> [Bool]
g3 a = sortValues (set1 (\b -> b) failed)

level2 :: [[Bool]]
level2 = sortValues (set1 g3 True)

-- ownflag: the inner set function fails inside its own body (an inside
-- failure: its set is empty), under the box of the outer argument.  [0]
sizeG :: Int
sizeG = length (sortValues (set1 gFail (0 :: Int)))

gFail :: Int -> Int
gFail _ = failed

ownflag :: [Int]
ownflag = sortValues (set1 id sizeG)

-- set0Inner: a is a captured variable of the inner set0, so the compiler
-- lifts set0 (id a) into set1 L a (decision D28 of 2026-10-12) and the
-- inner capsule boxes a under its own guard, over the guard of the outer
-- argument.  The inner capsule meets the failure as an outside failure
-- that entered the chain at the outer level, has no value and no inside
-- failure, so it fails, and the failure goes under the outer guard (the
-- record at the innermost level), where the outer capsule fails in turn.
-- No value, as before the lift, when the inner capsule met the failure
-- through the outer guard alone.
set0Inner :: [[Int]]
set0Inner = sortValues (set1 (\a -> sortValues (set0 (id a))) (failed :: Int))

-- set0InnerV: the same with a value of the inner function beside it: the
-- inner set stands with the value.  [[7]]
set0InnerV :: [[Int]]
set0InnerV = sortValues (set1 (\a -> sortValues (set0 (id a ? 7))) (failed :: Int))

-- mixed: an inside failure and an outside failure meet in one capsule
-- beside a value: the set holds the value.  [2]
mixed :: [Int]
mixed = sortValues (set1 (\a -> (a + 1) ? (failed ? 2)) failed)

-- mixedE: the same without the value: the set is empty.  True
mixedE :: Bool
mixedE = isEmpty (set1 (\a -> (a + 1) ? failed) failed)

-- t1c: the lambda closes over the failure (a captured argument is boxed).
-- [True]
t1c :: [Bool]
t1c = sortValues (let x = failed in set1 (\a -> x ? a) True)

-- argFail: one alternative of the argument fails: [0], and no value.
argFail :: [Int]
argFail = sortValues (set1 id (0 ? failed))

-- cycleInside, cycleInsideS: an alternative of the function dies through
-- a failed constraint step at the root (the occurs check of the union of
-- two classes: x is decided outside the capsule, so no narrowing with a
-- failing sibling happens inside), beside the failure of the argument.
-- The failed constraint is an inside failure, so the set stands empty:
-- True, [].  Before the record of a failed constraint the Python backend
-- failed the capsule (no value) where the C++ backend met a failure cell
-- in a sibling alternative and printed True.  KiCS2 has no occurs check,
-- so it is no reference here; the reading is that of rule (d1): the path
-- of the failure crossed no guard.
data T = T T

isT :: T -> Bool
isT (T _) = True

unT :: T -> T
unT (T t) = t

cycleOr :: T -> Bool -> Bool
cycleOr x a = a ? ((unT x =:= y) &> (x =:= y) &> True) where y free

cycleInside :: Bool
cycleInside = isT x &> isEmpty (set1 (cycleOr x) failed) where x free

cycleInsideS :: [Bool]
cycleInsideS = isT x &> sortValues (set1 (cycleOr x) failed) where x free
