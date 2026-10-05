-- Programs for unit_cxx_gc.py.
module CxxGc where

import Control.SetFunctions

-- Walks a list by a tail call.  Every cell is garbage once it is passed.
lastOf :: [Int] -> Int
lastOf (x:xs) = if null xs then x else lastOf xs

-- Allocates about 40 nodes per element, all short-lived, and returns n.
walk :: Int -> Int
walk n = lastOf [1..n]

-- A value with about ten nodes per element.
table :: Int -> [(Int, String)]
table n = [ (i, show i) | i <- [1..n] ]

-- Every alternative is an application.  (A set function whose value is the
-- guarded argument itself is covered by unit_cxx_scheduler.py.)
coin :: Int -> Int
coin x = (x + 0) ? (x + 1) ? (x + 2)

-- Consumes the values of a set function one at a time and walks n cells
-- after each one.  With a low threshold the collector runs between two
-- values, while the alternatives not produced yet wait in the queue of the
-- set function.  The result is 3 * n + 6.
spaced :: Int -> Int
spaced n = foldValues (\v acc -> v + walk n + acc) 0 (set1 coin 1)

-- Walks n cells inside a set function, so the allocation happens in a
-- nested evaluation.  The result is [n].
inner :: Int -> [Int]
inner n = sortValues (set1 walk n)

-- Programs for the ownership of configurations, queues, and sets
-- (TestOwnership).

-- Sorts by permutation: a fork per element inserted and a dropped
-- configuration per unsorted prefix.  psort n is [1..n].
insert :: Int -> [Int] -> [Int]
insert x [] = [x]
insert x (y:ys) = x:y:ys ? y : insert x ys

perm :: [Int] -> [Int]
perm [] = []
perm (x:xs) = insert x (perm xs)

sorted :: [Int] -> [Int]
sorted [] = []
sorted [x] = [x]
sorted (x:y:ys) | x <= y = x : sorted (y:ys)

psort :: Int -> [Int]
psort n = sorted (perm [n, n-1 .. 1])

-- A choice of the argument escapes the set function while its queue holds
-- two configurations, because the inner choice forked first.  The queue
-- splits, and both queues hold the configurations that have not made the
-- outer choice.  The values are {1,2} for 0 and {2,3} for 1.
plusChoice :: Int -> Int
plusChoice x = (1 ? 2) + x

escaped :: [Int]
escaped = sortValues (set1 plusChoice (0 ? 1))

-- A balanced choice tree of 2^n leaves.  The scheduler forks level by
-- level, so the first value comes after 2^n - 1 forks.  Every leaf is an
-- application (see coin).
tree :: Int -> Int -> Int
tree n x = if n == 0 then x + 0 else tree (n-1) x ? tree (n-1) (x+1)

-- A set function per item, consumed only in part: notEmpty takes the first
-- value and leaves 2^n - 1 configurations in the queue.  The items come
-- from Python, so a test reads the counters of the collector between them.
partial :: Int -> [Int] -> Int
partial n xs = length [ x | x <- xs, notEmpty (set1 (tree n) x) ]

-- An error inside a set function.
boom :: Int -> Int
boom x = error "boom" + x

boomSet :: [Int]
boomSet = sortValues (set1 boom 1)

-- The queens of QueensSet9 for a small board, through a set function.
queens :: Int -> [Int]
queens n | isEmpty ((set1 unsafe) p) = p
 where
   p = permutation [1..n]
   unsafe (_++[x]++y++[z]++_) = abs (x-z) =:= length y + 1

permutation :: [Int] -> [Int]
permutation [] = []
permutation (x:xs) = ndinsert (permutation xs)
 where
  ndinsert ys     = x : ys
  ndinsert (y:ys) = y : ndinsert ys

countQueens :: Int -> Int
countQueens n = length (sortValues (set1 queens n))

-- Programs for the stress mode of the collector (TestStress).

-- The ground normal form of an argument that binds its own free variable.
-- A collection in the middle of the normalization must not suspend the
-- configuration on the variable: the next steps bind it.
groundOwn :: Int
groundOwn = id $## (let x free in (x =:= 1) &> x)

-- Programs for the counters of the collector (unit_cxx_gc_counters.py).

-- Builds n thunks under a spine, forces the spine, then forces the thunks.
-- With a low threshold the thunks survive a collection before they are
-- stepped, so each of those steps writes an old redex.  The result is
-- n + sum [2..n+1].
thunks :: Int -> Int
thunks n = let xs = map (+1) [1..n] in lenStrict 0 xs + sumStrict 0 xs

-- The length and the sum by a tail call with a strict accumulator; those of
-- the Prelude recurse as deep as the list is long.
lenStrict :: Int -> [Int] -> Int
lenStrict acc []     = acc
lenStrict acc (_:xs) = (lenStrict $! acc + 1) xs

sumStrict :: Int -> [Int] -> Int
sumStrict acc []     = acc
sumStrict acc (x:xs) = (sumStrict $! acc + x) xs
