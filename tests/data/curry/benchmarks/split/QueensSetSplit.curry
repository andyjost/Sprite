-- QueensSet, split by hand for the process-split experiment of the
-- parallel-evaluation gate (the split suite of the benchmark harness; see
-- tests/README).  The whole is QueensSet: the placements of eight queens as
-- the permutations of [1..8] for which the set of unsafe pairs is empty.
--
-- perm applies ndinsert for the first element of the list to the
-- permutations of the rest; the first rule puts the element in front, the
-- second passes the head of the rest and inserts behind it.  A part fixes
-- the first element of the permutation: permFirst j is the sub-tree of
-- perm [1..n] in which ndinsert took its second rule for 1 .. j-1 and its
-- first rule for j, so 1 .. j-1 are inserted into the permutations of
-- j+1 .. n.  Part i of k takes the first elements congruent to i+1 modulo
-- k, joined by ?.  The parts of a split partition the permutations.  part
-- and permsPart take the size, so a test can check the partition at a
-- small size; the goals part2_0 .. part8_7 are the parts at the size of
-- QueensSet.

import Control.SetFunctions

perm [] = []
perm (x:xs) = ndinsert (perm xs)
 where
  ndinsert ys     = x : ys
  ndinsert (y:ys) = y : ndinsert ys

queens n | isEmpty ((set1 unsafe) p) = p
 where
   p = perm [1..n]

   unsafe (_++[x]++y++[z]++_) = abs (x-z) =:= length y + 1

-- The permutations of [1..n], and the whole program.
perms :: Int -> [Int]
perms n = perm [1..n]

whole :: Int -> [Int]
whole n = queens n

main = queens 8

-- permFirst j n: the permutations of [1..n] with j first.
permFirst :: Int -> Int -> [Int]
permFirst j n = j : perm ([1..j-1] ++ [j+1..n])

-- firsts n k i: the first elements of part i of k.
firsts :: Int -> Int -> Int -> [Int]
firsts n k i = [i+1, i+1+k .. n]

-- permsPart n k i: the permutations of [1..n] that part i of k generates.
permsPart :: Int -> Int -> Int -> [Int]
permsPart n k i = foldr1 (?) [permFirst j n | j <- firsts n k i]

-- part n k i: part i of k of the whole program.
part n k i | isEmpty ((set1 unsafe) p) = p
 where
   p = permsPart n k i

   unsafe (_++[x]++y++[z]++_) = abs (x-z) =:= length y + 1

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
