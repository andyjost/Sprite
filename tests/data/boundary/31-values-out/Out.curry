module Out where

data Item = A | B | C deriving (Eq, Show)

items :: [Item]
items = [A, B, C]

emptyString :: String
emptyString = ""

pairs :: [(String, Int)]
pairs = [("", 0), ("ab", 1)]

inc :: Int -> Int
inc x = x + 1

coin :: Int
coin = 1 ? 2

freeList :: [Int]
freeList = [x] where x free
