
split :: [Bool] -> ([Bool],[Bool])
split (x++y) = (x,y)
main = split [x,True] where x free