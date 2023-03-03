-------------------------------------------------------------------------
-- Example for the use of set functions as described in the paper

-- Sergio Antoy, Michael Hanus:
-- Set Functions for Functional Logic Programming
-- Proc. 11th International ACM SIGPLAN Conference on Principles and Practice
-- of Declarative Programming (PPDP'09), pp. 73-82, 2009 

import Control.SetFunctions

-------------------------------------------------------------------------
-- Solving the n-queens problem in Curry with set functions

-- Permutations of a list defined as a non-deterministic operation
perm [] = []
perm (x:xs) = ndinsert (perm xs)
 where
  ndinsert ys     = x : ys
  ndinsert (y:ys) = y : ndinsert ys

-- A placement is a solution if it is not unsafe.
-- Set functions are used to negate unsafe, and unsafe is defined
-- with a functional pattern.
queens n | isEmpty ((set1 unsafe) p) = p
 where
   p = perm [1..n]

   unsafe (_++[x]++y++[z]++_) = abs (x-z) =:= length y + 1

main = queens 10

-------------------------------------------------------------------------
