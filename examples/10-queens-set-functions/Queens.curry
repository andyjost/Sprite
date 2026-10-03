-- N queens with set functions.
--
-- This is the QueensSet program from the paper
--   Sergio Antoy and Michael Hanus, "Set Functions for Functional Logic
--   Programming", PPDP 2009,
-- with a type signature on every top-level function.

import Control.SetFunctions

-- One permutation of the list.  Because ndinsert is non-deterministic, the
-- program means every permutation.
perm :: [Int] -> [Int]
perm []     = []
perm (x:xs) = ndinsert x (perm xs)

-- Inserts x at the front of the list, or somewhere further in.  Both rules
-- apply to a non-empty list, so the result is a choice.
ndinsert :: Int -> [Int] -> [Int]
ndinsert x ys     = x : ys
ndinsert x (y:ys) = y : ndinsert x ys

-- A placement is a solution when the set of its unsafe pairs is empty.  The
-- set function (set1 unsafe) collects every value of (unsafe p), so isEmpty
-- negates the non-deterministic predicate unsafe.
queens :: Int -> [Int]
queens n | isEmpty (set1 unsafe p) = p
  where p = perm [1..n]

-- The functional pattern names any two queens x and z with the queens y
-- between them.  The pair is unsafe when the two queens share a diagonal.
unsafe :: [Int] -> Bool
unsafe (_ ++ [x] ++ y ++ [z] ++ _) = abs (x - z) =:= length y + 1
