module Str where

-- The names of a table: the first component of each row.
names :: [(String, Int)] -> [String]
names table = map fst table

-- A string and a number in one text.
strInTuple :: (String, Int) -> String
strInTuple (s, n) = s ++ show n
