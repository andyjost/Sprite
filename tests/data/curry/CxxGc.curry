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

-- Every alternative is an application: a set function whose value is the
-- guarded argument itself is not supported by the C++ backend.
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
