append :: [t] -> [t] -> [t]
append []     x  = x
append (x:xs) ys = x : append xs ys

rev :: [t] -> [t]
rev []     = []
rev (x:xs) = append (rev xs) [x]

main :: [Int]
main = rev [1,2,3,4]
