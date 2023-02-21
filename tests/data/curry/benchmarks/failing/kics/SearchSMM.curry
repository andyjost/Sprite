-- Variante a
permute :: [a] -> [a]
permute []     = []
permute (x:xs) = ndinsert x $ permute xs

ndinsert :: a -> [a] -> [a]
ndinsert x [] = [x]
ndinsert x (y:ys) = x:y:ys ? y:ndinsert x ys

-- Variante b: weniger strikt
perm :: [a] -> [a]
perm [] = []
perm (x:xs) = insert x (perm xs)

insert :: a -> [a] -> [a]
insert x xs = x:xs
insert x (y:ys) = y : insert x ys

add :: [Int] -> [Int] -> [Int]
add xs ys = add' (reverse xs) (reverse ys) []

add' :: [Int] -> [Int] -> [Int] -> [Int]
add' [] ys@(_:_)   res = reverse ys ++ res
add' xs []         res = reverse xs ++ res
add' (x:xs) (y:ys) res
  | x+y < 10  = add' xs ys $ (x+y):res
  | otherwise = add' (inc xs) ys $ ((x+y) `mod` 10):res

inc :: [Int] -> [Int]
inc [] = [1]
inc (x:xs)
  | x == 9    = 0 : inc xs
  | otherwise = (x+1) : xs

smma :: [Int]
smma = let [s,e,n,d,m,o,r,y] = take 8 $ permute [0..9] in
       if s > 0 && m > 0 && [s,e,n,d] `add` [m,o,r,e] == [m,o,n,e,y]
          then [s,e,n,d,m,o,r,y]
          else failed

smmb :: [Int]
smmb = let [s,e,n,d,m,o,r,y] = take 8 $ perm [0..9] in
       if s > 0 && m > 0 && [s,e,n,d] `add` [m,o,r,e] == [m,o,n,e,y]
         then [s,e,n,d,m,o,r,y]
         else failed

main = smmb
