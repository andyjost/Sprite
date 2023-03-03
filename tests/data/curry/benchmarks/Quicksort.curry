-- quicksort using higher-order functions:

qsort :: [Int] -> [Int]
qsort []     = []
qsort (x:l)  = qsort (filter (<x) l) ++ x : qsort (filter (>=x) l)

goal = qsort ([1001..3000]++[1..1000])

main = goal
