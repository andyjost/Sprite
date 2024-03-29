-- Compute the number of solutions to queens placements
-- Uses prelude operations and list comprehensions.

queens nq = length (gen nq)
 where
  gen :: Int -> [[Int]]
  gen n = if n==0
          then [[]]
          else [ (q:b) | b <- gen (n-1), q <- [1..nq], safe q 1 b]

safe :: Int -> Int -> [Int] -> Bool
safe _ _ [] = True
safe x d (q:l) = x /= q && x /= q+d && x /= q-d && safe x (d+1) l

main = queens 8
