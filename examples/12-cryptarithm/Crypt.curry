-- A general solver for cryptarithms such as SEND + MORE = MONEY.
--
-- Every letter stands for one digit.  Different letters stand for different
-- digits.  No word starts with 0.  The solver takes the addends and the
-- result as strings and returns one assignment of digits to letters.  Each
-- solution of the puzzle is one value of solveCrypt.

module Crypt where

import Data.List (maximum, nub, sum)

-- An assignment of digits to letters.
type Env = [(Char, Int)]

-- Returns an assignment that makes the sum hold.
--
-- The letters are listed units column first and paired with a permutation
-- of the digits.  The permutation is built lazily by perm, so a letter
-- receives a digit only when a guard needs it.  The guard checks the columns
-- from the units column upward.  A permutation whose first digits break the
-- units column fails before the remaining letters receive a digit.
solveCrypt :: [String] -> String -> Env
solveCrypt addends result
  | all (columnOK env) [1 .. width] && sumOK env && all (leadingOK env) ws
  = env
  where
    ws      = addends ++ [result]
    width   = maximum (map length ws)
    letters = nub (concatMap (column ws) [1 .. width])
    env     = zip letters (perm [0 .. 9])
    -- The last k digits of the sum of the addends match the last k digits
    -- of the result.
    columnOK e k = sum (map (value e . lastN k) addends) `mod` (10 ^ k)
                     == value e (lastN k result)
    -- The complete sum holds.  This also rejects a carry out of the top
    -- column.
    sumOK e = sum (map (value e) addends) == value e result
    leadingOK e w = digit e (head w) /= 0

-- The letters in column k, counted from the units column.  A word shorter
-- than k has no letter there.
column :: [String] -> Int -> String
column ws k = [ reverse w !! (k - 1) | w <- ws, k <= length w ]

-- The last k letters of a word.
lastN :: Int -> String -> String
lastN k w = drop (length w - k) w

-- The number a word stands for under an assignment.
value :: Env -> String -> Int
value env w = foldl (\acc c -> 10 * acc + digit env c) 0 w

digit :: Env -> Char -> Int
digit env c = case lookup c env of Just d -> d

-- One permutation of the list.  Each permutation is one value.
perm :: [Int] -> [Int]
perm []     = []
perm (x:xs) = ndinsert x (perm xs)

-- Inserts x at one position of the list.  Each position is one value.
ndinsert :: Int -> [Int] -> [Int]
ndinsert x ys     = x : ys
ndinsert x (y:ys) = y : ndinsert x ys
