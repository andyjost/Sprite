-- A search for a program: the shortest composition of basic operations
-- that hashes a fixed set of keys into a table without a collision.
module PerfectHash where

data Op = Mul Int | Shr Int | Add Int

m32 :: Int
m32 = 4294967296

hash :: [Op] -> Int -> Int
hash [] x = x
hash (Mul c : ops) x = hash ops ((x * c) `mod` m32)
hash (Shr k : ops) x = hash ops (x `div` (2 ^ k))
hash (Add c : ops) x = hash ops ((x + c) `mod` m32)

-- One operation, chosen from a small set: nine alternatives.
op :: Op
op = Mul (anyOf [31, 33, 37, 65599]) ? Shr (anyOf [2, 4]) ? Add (anyOf [1, 7, 13])

-- Every program of a given length.
program :: Int -> [Op]
program n
  | n == 0 = []
  | n > 0 = op : program (n - 1)

-- A key as a number: the classic fold with 31.
key :: String -> Int
key = foldl (\h c -> (h * 31 + ord c) `mod` m32) 7

injective :: [Int] -> Bool
injective [] = True
injective (x:xs) = x `notElem` xs && injective xs

-- A program of length n that is perfect for the keys in a table of the
-- given size.  Nondeterminism enumerates the programs; the guard keeps the
-- perfect ones.
perfect :: [String] -> Int -> Int -> [Op]
perfect keys size n | injective (map slot keys) = p
  where p = program n
        slot k = hash p (key k) `mod` size
