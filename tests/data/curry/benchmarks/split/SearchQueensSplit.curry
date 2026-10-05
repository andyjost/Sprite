-- SearchQueens, split by hand for the process-split experiment of the
-- parallel-evaluation gate (the split suite of the benchmark harness; see
-- tests/README).  The whole is SearchQueens: the placements of eight queens
-- as the permutations of [1..8] that pass allSafe, where permute narrows
-- the free list u of each element to find its position.
--
-- A part fixes the position of the first element.  With u a list of i free
-- variables, permuteAt i gives the permutations with the first element at
-- position i: the sub-space of permute in which the narrowing of u took
-- the branch (_:_) i times and then [].  Part i of k takes the positions
-- congruent to i modulo k, joined by ?.  The parts of a split partition the
-- permutations.  part and permsPart take the size, so a test can check the
-- partition at a small size; the goals part2_0 .. part8_7 are the parts at
-- the size of SearchQueens.

permute :: Prelude.Data a => [a] -> [a]
permute [] = []
permute (x:xs) | u++v =:= permute xs = u++(x:v) where u,v free

allSafe :: [Int] -> Bool
allSafe qs = allSafe' $ zip qs [1..] where
  allSafe' :: [(Int,Int)] -> Bool
  allSafe' [] = True
  allSafe' (xy:xys) = all (safe xy) xys && allSafe' xys

safe :: (Int,Int) -> (Int,Int) -> Bool
safe (a,b) (c,d) = abs (a-c) /= abs (b-d)

abs :: Int -> Int
abs x | x < 0     = -x
      | otherwise = x

queens :: Int -> [Int]
queens n | allSafe qs = qs where qs = permute [1..n]

-- The permutations of [1..n], and the whole program.
perms :: Int -> [Int]
perms n = permute [1..n]

whole :: Int -> [Int]
whole n = queens n

main = queens 8

-- freeList i: a list of i free variables.
freeList :: Prelude.Data a => Int -> [a]
freeList i | i == 0    = []
           | otherwise = x : freeList (i-1) where x free

-- permuteAt i xs: the permutations of xs with the first element of xs at
-- position i.
permuteAt :: Prelude.Data a => Int -> [a] -> [a]
permuteAt i (x:xs) | u++v =:= permute xs = u++(x:v)
  where u = freeList i
        v free

-- positions n k i: the positions of part i of k.
positions :: Int -> Int -> Int -> [Int]
positions n k i = [i, i+k .. n-1]

-- permsPart n k i: the permutations of [1..n] that part i of k generates.
permsPart :: Int -> Int -> Int -> [Int]
permsPart n k i = foldr1 (?) [permuteAt p [1..n] | p <- positions n k i]

-- part n k i: part i of k of the whole program.
part :: Int -> Int -> Int -> [Int]
part n k i | allSafe qs = qs where qs = permsPart n k i

part2_0 = part 8 2 0
part2_1 = part 8 2 1

part4_0 = part 8 4 0
part4_1 = part 8 4 1
part4_2 = part 8 4 2
part4_3 = part 8 4 3

part8_0 = part 8 8 0
part8_1 = part 8 8 1
part8_2 = part 8 8 2
part8_3 = part 8 8 3
part8_4 = part 8 8 4
part8_5 = part 8 8 5
part8_6 = part 8 8 6
part8_7 = part 8 8 7
