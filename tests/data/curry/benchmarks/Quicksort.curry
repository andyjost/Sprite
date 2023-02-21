-- quicksort using higher-order functions:

qsort :: [Int] -> [Int] 
qsort []     = []
qsort (x:l)  = qsort (filter (<x) l) ++ x : qsort (filter (>=x) l)

goal = qsort ([251..500]++[1..250])

main = goal
