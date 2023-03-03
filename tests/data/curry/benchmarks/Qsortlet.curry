-- quicksort using a split function (demonstrating where/let declarations):

split _ [] = ([],[])
split e (x:xs) | e>=x  = (x:l,r)
               | e<x   = (l,x:r)
               where (l,r) = split e xs


qsort []     = []
qsort (x:xs) = let (l,r) = split x xs
               in qsort l ++ (x:qsort r)

goal :: [Int]
goal = qsort ([501..1000]++[1..500])

main = goal
