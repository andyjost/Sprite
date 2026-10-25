permute :: [a] -> [a]
permute [] = []
permute (x:xs) | u++v =:= permute xs = u++(x:v) where u,v free

allSafe :: [Int] -> Bool
allSafe qs = allSafe' $ zip qs [1..] where
  allSafe' :: [(Int,Int)] -> Bool
  allSafe' [] = True
  allSafe' (xy:xys) = all (safe xy) xys && allSafe' xys

safe :: (Int,Int) -> (Int,Int) -> Bool
safe (a,b) (c,d) = abs (a-c) /= abs (b-d)

abs :: Int -> Int
abs x | x < 0     = -x
      | otherwise = x

queens :: Int -> [Int]
queens n | allSafe qs = qs where qs = permute [1..n]

main = queens 8
