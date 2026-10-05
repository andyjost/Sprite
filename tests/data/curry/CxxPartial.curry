-- Programs for unit_cxx_partial.py: the flat partial applications of the
-- C++ backend.  A partial application holds its arguments inline, and a
-- function used as a value (a partial application without arguments) is
-- one node per module.
module CxxPartial where

import Control.SetFunctions

plus2 :: Int -> Int -> Int
plus2 a b = a + b

plus3 :: Int -> Int -> Int -> Int
plus3 a b c = a + b + c

inc :: Int -> Int
inc x = x + 1

-- An unknown call: the function goes through apply.
app :: (a -> b) -> a -> b
app f x = f x

-- Partial applications of no, one, and two arguments, completed by apply.
zero, one, two :: Int
zero = app (app (app plus3 1) 2) 3
one = app (app (plus3 1) 2) 3
two = app (plus3 1 2) 3

-- A function value applied twice: the shared node is not changed by apply.
twice :: Int
twice = let f = plus3 1 in f 2 3 + f 3 2

-- A function of 36 parameters: a partial application of 32 or more
-- arguments has an info table outside the cached range of the family.
many :: Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int
many a1 a2 a3 a4 a5 a6 a7 a8 a9 a10 a11 a12 a13 a14 a15 a16 a17 a18 a19 a20 a21 a22 a23 a24 a25 a26 a27 a28 a29 a30 a31 a32 a33 a34 a35 a36 = a1 + a2 + a3 + a4 + a5 + a6 + a7 + a8 + a9 + a10 + a11 + a12 + a13 + a14 + a15 + a16 + a17 + a18 + a19 + a20 + a21 + a22 + a23 + a24 + a25 + a26 + a27 + a28 + a29 + a30 + a31 + a32 + a33 + a34 + a35 + a36

-- The partial application of 35 arguments, completed by apply.
manyPartial :: Int
manyPartial = app (many 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35) 36

-- Partial applications of 32, 33, 34, and 35 arguments, made by apply.
manyApply :: Int
manyApply = app (app (app (app (many 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32) 33) 34) 35) 36

-- A constructor as a function value, and a section.
justs :: [Maybe Int]
justs = map Just [1, 2]

sections :: [Int]
sections = map (+ 1) [1, 2] ++ map (\x -> x * 2) [3]

-- Two partial applications with the same arguments, in one list.
partials :: [Int -> Int]
partials = [plus3 1 2, plus3 1 2]

-- One function value twice.
incTwice :: (Int -> Int, Int -> Int)
incTwice = (inc, inc)

-- A step that spells a function value; its result fits the redex.
applyInc :: Int -> Int -> Int
applyInc x _ = app inc x

-- A loop that spells a function value in every iteration.
loop :: Int -> Int -> Int
loop acc n = if n == 0 then acc else loop (app inc acc) (n - 1)

-- Set functions over partial applications of several arguments.
setf :: Int -> Int -> Int -> Int
setf x y z = (x ? y) + z

set3Values :: [Int]
set3Values = sortValues (set3 setf 1 2 3)

set0Value :: [Int]
set0Value = sortValues (set0 (1 ? 2))

set1Lambda :: [Int]
set1Lambda = sortValues (set1 (\x -> x ? 10) 1)

set1Partial :: [Int]
set1Partial = sortValues (set1 (plus3 1 2) (3 ? 4))

set2Many :: [Int]
set2Many = sortValues (set2 (many 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34) (35 ? 0) 36)
