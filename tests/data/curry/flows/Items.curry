module Items where

data Item = A | B | C deriving (Eq, Show)

countItems :: [Item] -> Int
countItems = length

applyAll :: [Int -> Int] -> Int -> [Int]
applyAll fs x = map (\f -> f x) fs

inc :: Int -> Int
inc x = x + 1

dbl :: Int -> Int
dbl x = x * 2
