-- PermSort, split by hand for the process-split experiment of the
-- parallel-evaluation gate (the split suite of the benchmark harness; see
-- tests/README).  The whole is PermSort: psort of the fourteen elements
-- 2, 14, 13 .. 3, 1.
--
-- perm inserts the elements from the back, so insert 3 into [1] forks first
-- (3 in front, or 1 in front and 3 behind it), then insert 4 into that
-- result, then insert 5, and so on; the first element of the input, 2, is
-- inserted last.  A part fixes the first of those choices: the i-th of
-- k = 2^d parts follows the d binary digits of i through the first d
-- insertions (a one bit takes the first alternative of insert) and inserts
-- the other elements on top as perm does.  The parts of a split partition
-- the permutations: every permutation of the input comes from exactly one
-- part.  part and permsPart take the size, so a test can check the
-- partition at a small size; the goals part2_0 .. part8_7 are the parts at
-- the size of PermSort.

insert x [] = [x]
insert x (y:ys) = x:y:ys ? y : (insert x ys)

perm [] = []
perm (x:xs) = insert x (perm xs)

sorted :: [Int] -> [Int]
sorted []       = []
sorted [x]      = [x]
sorted (x:y:ys) | x <= y = x : sorted (y:ys)

psort xs = sorted (perm xs)

input :: Int -> [Int]
input n = 2:[n,n-1 .. 3]++[1]

-- The permutations of the input, and the whole program.
perms :: Int -> [Int]
perms n = perm (input n)

whole :: Int -> [Int]
whole n = sorted (perms n)

main = whole 14

-- insertAll xs s: the elements of xs inserted into s, the last of xs first,
-- as perm inserts the elements of a list into [].
insertAll :: [Int] -> [Int] -> [Int]
insertAll [] s = s
insertAll (x:xs) s = insert x (insertAll xs s)

-- fixed bs es s: the partial permutation after the choices bs on the
-- insertions of the first elements of es into s, and the elements left.
-- True takes the first alternative of insert (the element goes in front);
-- False takes the second (the head stays and the element goes behind it).
fixed :: [Bool] -> [Int] -> [Int] -> ([Int], [Int])
fixed [] es s = (s, es)
fixed (b:bs) (e:es) (y:ys) =
  fixed bs es (if b then e:y:ys else y : insert e ys)

-- digits k i: the binary digits of i, the most significant first, as many as
-- k = 2^d has.
digits :: Int -> Int -> [Bool]
digits k i | k <= 1    = []
           | otherwise = digits (k `div` 2) (i `div` 2) ++ [i `mod` 2 == 1]

-- permsPart n k i: the permutations of input n that part i of k generates.
-- The elements are inserted in the order 3, 4 .. n, 2 into [1].
permsPart :: Int -> Int -> Int -> [Int]
permsPart n k i = insertAll (reverse rest) s
  where (s, rest) = fixed (digits k i) (reverse (take (n-1) (input n))) [1]

-- part n k i: part i of k of the whole program.
part :: Int -> Int -> Int -> [Int]
part n k i = sorted (permsPart n k i)

part2_0 = part 14 2 0
part2_1 = part 14 2 1

part4_0 = part 14 4 0
part4_1 = part 14 4 1
part4_2 = part 14 4 2
part4_3 = part 14 4 3

part8_0 = part 14 8 0
part8_1 = part 14 8 1
part8_2 = part 14 8 2
part8_3 = part 14 8 3
part8_4 = part 14 8 4
part8_5 = part 14 8 5
part8_6 = part 14 8 6
part8_7 = part 14 8 7
