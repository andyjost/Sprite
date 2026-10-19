-- A binary tree, taken apart in Curry here and in Python in go.py.
module Tree where

data Tree a = Leaf | Node (Tree a) a (Tree a)

-- The number of nodes, the depth, and the number of leaves.
size :: Tree a -> Int
size Leaf = 0
size (Node l _ r) = size l + 1 + size r

depth :: Tree a -> Int
depth Leaf = 0
depth (Node l _ r) = 1 + max (depth l) (depth r)

leaves :: Tree a -> Int
leaves Leaf = 1
leaves (Node l _ r) = leaves l + leaves r

-- The values in order.
toList :: Tree a -> [a]
toList Leaf = []
toList (Node l x r) = toList l ++ [x] ++ toList r

-- A search tree.
insert :: Ord a => a -> Tree a -> Tree a
insert x Leaf = Node Leaf x Leaf
insert x t@(Node l y r)
  | x < y     = Node (insert x l) y r
  | x > y     = Node l y (insert x r)
  | otherwise = t

fromList :: Ord a => [a] -> Tree a
fromList = foldr insert Leaf

member :: Ord a => a -> Tree a -> Bool
member x t = x `elem` toList t

-- Every shape with n nodes: a nondeterministic generator.  There are
-- five shapes with three nodes (the Catalan numbers).
shapes :: Int -> Tree ()
shapes 0 = Leaf
shapes n | n > 0 = Node (shapes k) () (shapes (n - 1 - k))
  where k = anyOf [0 .. n - 1]

-- A reproducible pseudo-random tree: the branch sizes and the values follow
-- a linear congruential sequence from the seed.  No randomness in the
-- runtime: the same seed gives the same tree everywhere.
randomTree :: Int -> Int -> Tree Int
randomTree _ 0 = Leaf
randomTree seed n | n > 0 =
  let s = step seed
      k = s `mod` n
  in Node (randomTree s k) (s `mod` 100) (randomTree (step s) (n - 1 - k))

step :: Int -> Int
step s = (s * 1103515245 + 12345) `mod` 2147483648
