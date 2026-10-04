-- Programs for unit_cxx_scheduler.py: set functions whose value is a
-- sub-term of the guarded argument, and steps of a nested set function
-- that are interrupted while they hold a residual.
module CxxScheduler where

import Control.SetFunctions
import Data.List (last, tails)

-- The value of the set function is the guarded argument itself, so the
-- guard of the argument reaches the root of the nested configuration.
idSet :: Int -> [Int]
idSet x = sortValues (set1 id x)

emptyId :: Bool
emptyId = isEmpty (set1 id 1)

-- The values are the elements of the argument.
anyOf :: [a] -> a
anyOf (x:xs) = x ? anyOf xs

anyOfSet :: [Int] -> [Int]
anyOfSet xs = sortValues (set1 anyOf xs)

-- The value contains the argument as a sub-term.
tailsSet :: [Int] -> [[[Int]]]
tailsSet xs = sortValues (set1 tails xs)

headOrLast :: [Int] -> Int
headOrLast xs = head xs ? last xs

headOrLastSet :: [Int] -> [Int]
headOrLastSet xs = sortValues (set1 headOrLast xs)

-- A choice of the argument escapes the set function: two values.
argChoice :: [Int]
argChoice = sortValues (set1 id (1 ? 2))

-- The guarded argument is a free variable.
freeId :: [Int]
freeId = sortValues (set1 id x) where x free

-- Nested set functions.  The inner one returns its argument, which carries
-- the guards of both set functions.
inner :: Int -> [Int]
inner x = sortValues (set1 id x)

nestedPlain :: [[Int]]
nestedPlain = sortValues (set1 inner 1)

nested :: [[Int]]
nested = sortValues (set1 inner (1 ? 2))

-- The inner function captures the argument of the outer one instead of
-- receiving it as its own argument.  The argument carries the guard of the
-- outer set function only, so the inner set function encapsulates the
-- choice (a known limitation of both backends).
constant :: Int -> Int -> Int
constant x _ = x

captured :: Int -> [Int]
captured x = sortValues (set1 (constant x) 0)

nestedCapture :: [[Int]]
nestedCapture = sortValues (set1 captured (1 ? 2))

-- Programs for the interrupted step (TestInterruptedStep).

lastOf :: [Int] -> Int
lastOf (x:xs) = if null xs then x else lastOf xs

strict :: Bool -> Bool
strict True = True
strict False = False

-- d strict applications around b.  A constraint inside them is lifted one
-- level at a time, so the step that binds its variable spans d forward
-- nodes and a periodic rotation can land inside it.
nest :: Int -> Bool -> Bool
nest d b = if d == 0 then b else strict (nest (d - 1) b)

-- y =:= x unites the two variables with y as the root of the group.  The
-- non-strict equation then probes x, which records a residual for x and
-- for its group, and the group's residual stays until the constraint
-- reaches the root.
grouped :: Int -> Int -> Bool
grouped d n = let x, y free in (y =:= x) &> nest d (x =:<= n)

-- Walks k list cells, then evaluates the grouped constraint.
preamble :: Int -> Int -> Int -> Bool
preamble d k n = lastOf [1 .. k] > 0 && grouped d n

slow :: Int -> Int
slow m = if lastOf [1 .. m] > 0 then 3 else 0

-- A set function of one configuration beside a long alternative.  The
-- periodic rotation interrupts the set function after 65536 forward nodes;
-- with the right k it lands inside the grouped constraint.
rotated :: Int -> Int -> Int -> Int
rotated d k m = (if sortValues (set1 (preamble d k) 1) == [True] then 1 else 2)
                ? slow m

-- The right side of a strict equation nests deeper than the stack limit.
depth :: Int -> Int
depth d = if d == 0 then 0 else 1 + depth (d - 1)

unwoundIn :: Int -> Int
unwoundIn d = let x, y free in (y =:= x) &> ((x =:= depth d) &> 1)

-- The set function unwinds at the stack limit while its step holds the
-- group's residual.  The alternative 7 runs, and the stuck set function is
-- dropped with the stack error.
unwound :: Int -> Int
unwound d = (if sortValues (set1 unwoundIn d) == [1] then 1 else 2) ? 7
