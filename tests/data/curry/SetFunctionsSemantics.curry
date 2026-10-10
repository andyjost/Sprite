-- The programs of unit_setfunctions_semantics.py: the goals of the probe
-- table of the memo on the Fair Scheme proofs (sections 5.2 and 5.3 of the
-- memo of 2026-10-08), with their helpers as the probe modules define them.
-- Two rules are under test.  The captured arguments of the function value
-- of a set function are boxed as the value arguments are (decision D2,
-- issue #117): their non-determinism escapes the capsule.  A failure that
-- comes from an argument and is demanded inside the capsule fails the set
-- function under the flag setfunction_failures (decision D1).
module SetFunctionsSemantics where
import Control.SetFunctions

adj :: Int -> Int
adj i = (i - 1) ? (i + 1)

binDigit :: Int
binDigit = 0 ? 1

incr :: Int -> Int
incr i = i + 1

const1 :: a -> Int
const1 _ = 1

nilP :: [Int] -> Bool
nilP [] = True

pf :: Bool -> Int
pf True = 1

g :: Bool -> Int
g b = if b then 1 else 2

adjL :: Int -> [Int]
adjL x = sortValues (set1 adj x)

-- The case-swap pair of Christiansen et al. (PPDP 2013, section 5): g1
-- demands its first argument first, g2 its second.
g1 :: Int -> Int -> Int
g1 a b = case a of { 0 -> case b of { 0 -> 0; _ -> 1 }; _ -> 2 }

g2 :: Int -> Int -> Int
g2 a b = case b of { 0 -> case a of { 0 -> 0; _ -> 1 }; _ -> 2 }

constT :: a -> Int -> a
constT x _ = x

-- Section 1: the goals on which the two rules change nothing.

-- s1: the running example of the dissertation (section 4.3): two sets.
s1 :: [Int]
s1 = sortValues (set1 adj binDigit)

-- s2 of PG: the choice of the argument, shared with the pair.
s2PG :: ([Int], Int)
s2PG = let x = 0 ? 1 in (sortValues (set1 incr x), x)

-- s2 of PL: a failing argument that the function does not demand.
s2PL :: [Int]
s2PL = sortValues (set1 const1 failed)

-- s3 of PG: the same with a failing call as the argument.
s3PG :: [Int]
s3PG = sortValues (set1 const1 (head []))

-- s3i: a failure inside the function.
s3i :: Bool
s3i = isEmpty (set1 (\_ -> failed) (0 :: Int))

-- s4d: g2 demands the inner failure, created inside the capsule, first.
s4d :: Bool
s4d = isEmpty (set1 (\a -> g2 a failed) failed)

-- s5: nested set functions; the choice of the argument escapes both.
s5 :: [[Int]]
s5 = sortValues (set1 adjL binDigit)

-- nest2: a free argument variable, narrowed in the inner capsule, escapes
-- both.
nest2 :: [[Bool]]
nest2 = sortValues (set1 (\b -> sortValues (set1 not b)) x) where x free

-- s6 of PG: a free argument variable narrowed inside the capsule.
s6PG :: [Bool]
s6PG = sortValues (set1 not x) where x free

-- s7 of PG: a group made outside the capsule, narrowed inside.
s7PG :: ([Int], Bool)
s7PG = (x =:= y) &> (sortValues (set1 g y), not x) where x, y free

-- s7 of PL: a free argument variable narrowed inside, read outside.
s7PL :: ([Int], Bool)
s7PL = (sortValues (set1 (\b -> if b then 1 else 2) x), x) where x free

-- s8 of PL: the captured choice decided before the capsule starts.
s8PL :: [Int]
s8PL = let x = 0 ? 1 in (x `seq` sortValues (set1 (\y -> x + y) 10))

-- s9, s10: a failure of the function for one side of the argument.
s9 :: [Int]
s9 = sortValues (set1 pf (True ? False))

s10 :: [Int]
s10 = sortValues (set1 pf x) where x free

-- ho1: a non-deterministic function argument.
ho1 :: [Int]
ho1 = sortValues (set1 (adj ? id) 0)

-- cap1: the explicit capture of the non-determinism of an argument.
cap1 :: [Int]
cap1 = sortValues (evalS (set adj `captureS` (0 ? 1)))

-- ord1: the captured choice, decided by the pair before the capsule.
ord1 :: (Int, [Int])
ord1 = let x = 0 ? 1 in (x, sortValues (set1 (\y -> x + y) 10))

-- cin2: the outside variable as a boxed argument.
cin2 :: ([Bool], Bool)
cin2 = (sortValues (set2 (\x' y -> (x' =:= y) &> y) x True), x) where x free

-- cin3: the constraint between the captured variable and the argument,
-- the same variable.
cin3 :: ([Bool], Bool)
cin3 = (sortValues (set1 (\y -> (x =:= y) &> y) x), x) where x free

-- Section 2: the captured arguments (decision D2).  Each goal pairs the set
-- with the captured choice or variable, so that a value shows which side
-- the set belongs to.

-- s6 of PL: a captured choice the enclosing context has not decided.
s6PL :: [Int]
s6PL = let x = 0 ? 1 in sortValues (set1 (\y -> x + y) 10)

-- ord2: ord1 with the pair reversed, so that the capsule meets the choice
-- before the pair decides it.
ord2 :: ([Int], Int)
ord2 = let x = 0 ? 1 in (sortValues (set1 (\y -> x + y) 10), x)

-- ord2 with the choice as an argument of set2: the reference shape.
ord2Arg :: ([Int], Int)
ord2Arg = let x = 0 ? 1 in (sortValues (set2 (\x' y -> x' + y) x 10), x)

-- cin1: a strict constraint inside the capsule between a captured outside
-- variable and the argument.
cin1 :: ([Bool], Bool)
cin1 = (sortValues (set1 (\y -> (x =:= y) &> y) True), x) where x free

-- cin1 with the pair reversed.
cin1Rev :: (Bool, [Bool])
cin1Rev = (x, sortValues (set1 (\y -> (x =:= y) &> y) True)) where x free

-- A captured free variable narrowed by the function itself.
capNarrow :: ([Bool], Bool)
capNarrow = (sortValues (set1 (\_ -> not x) (0 :: Int)), x) where x free

-- The choice inside a data structure the function value captures.  The
-- whole captured argument is boxed, and the pattern match passes the box
-- on to the component.
capData :: ([Int], Int)
capData = let x = 0 ? 1 in let p = (x, 2 :: Int) in
  (sortValues (set1 (\y -> fst p + y) 10), x)

-- The choice inside a partial application the function value captures.
capPartial :: ([Int], Int)
capPartial = let x = 0 ? 1 in let f = (+) x in
  (sortValues (set1 (\y -> f y) 10), x)

-- The choice inside a partial application passed as a value argument and
-- applied inside the capsule.
argPartial :: ([Int], Int)
argPartial = let x = 0 ? 1 in
  (sortValues (set1 (\f -> f 0) (constT x)), x)

-- A captured choice in a nested set function: the inner function value
-- captures the argument of the outer set function.
capNested :: [[Int]]
capNested = sortValues (set1 (\x -> sortValues (set1 (constT x) 0)) (1 ? 2))

-- Section 3: failures from an argument (decision D1).  Under the flag
-- setfunction_failures 'escape', the default, the goals of this section
-- have no value where the comment says so; under 'encapsulate' every
-- failure drops its alternative and an empty queue gives the empty set.

-- s3: a failing argument that the function demands: [] and True, or no
-- value.
s3 :: [Int]
s3 = sortValues (set1 id failed)

s3e :: Bool
s3e = isEmpty (set1 id failed)

-- s4 of PG: the failing argument under a pattern match, and the same with a
-- failing call: [] or no value.
s4 :: [Bool]
s4 = sortValues (set1 nilP failed)

s4h :: [Bool]
s4h = sortValues (set1 nilP (head []))

-- s4a, s4b: both failures outside, one captured and one passed; g1 demands
-- the captured one first, g2 the passed one: True or no value.
s4a :: Bool
s4a = isEmpty (set1 (g1 failed) failed)

s4b :: Bool
s4b = isEmpty (set1 (g2 failed) failed)

-- s4c: the inner failure is created inside the capsule, and g1 demands the
-- argument first: True or no value.
s4c :: Bool
s4c = isEmpty (set1 (\a -> g1 a failed) failed)

-- The failing argument of the outer set function demanded inside the inner
-- capsule: both capsules fail.  False (the outer set holds the empty inner
-- set) or no value.
nestFail :: Bool
nestFail = isEmpty (set1 (\x -> sortValues (set1 id x)) (failed :: Int))

-- The failure is created inside the outer function and passed to the inner
-- set function: the inner set function fails, which drops the alternative
-- of the outer function.  False or True.
nestFailInner :: Bool
nestFailInner =
  isEmpty (set1 (\_ -> sortValues (set1 id (failed :: Int))) (0 :: Int))

-- A value produced before the failing argument is demanded stays a value
-- under both settings: the set is lazy.
lazyFirst :: Bool
lazyFirst = notEmpty (set1 (\x -> 1 ? x) failed)

-- A PartialS that is a value argument, applied inside the capsule with
-- applyS: the boxes of the arguments it holds stay outermost, so the inner
-- set function gives them its set and the choice escapes both capsules.
pS :: [[Int]]
pS = sortValues (set1 (\p -> sortValues (evalS (p `applyS` 1))) (set ((+) (0 ? 1))))

-- The same PartialS captured by the function value, paired with its choice.
pSCap :: ([[Int]], Int)
pSCap = let c = 0 ? 1 in let p = set ((+) c) in
  (sortValues (set1 (\y -> sortValues (evalS (p `applyS` y))) 1), c)
