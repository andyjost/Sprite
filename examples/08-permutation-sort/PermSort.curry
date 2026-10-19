-- The classic: a sorted permutation is a sort.
module PermSort where

import Control.SetFunctions

perm :: [a] -> [a]
perm [] = []
perm (x:xs) = insert x (perm xs)

insert :: a -> [a] -> [a]
insert x ys = x : ys
insert x (y:ys) = y : insert x ys

sorted :: Ord a => [a] -> Bool
sorted xs = and (zipWith (<=) xs (drop 1 xs))

sort :: Ord a => [a] -> [a]
sort xs | sorted ys = ys
  where ys = perm xs

-- The set functions: all the permutations, and all the sorted ones.  A set
-- function captures the nondeterminism of the function it lifts; a
-- choice outside the capsule stays outside.
permS :: [a] -> Values [a]
permS = set1 perm

sortS :: Ord a => [a] -> Values [a]
sortS = set1 sort
