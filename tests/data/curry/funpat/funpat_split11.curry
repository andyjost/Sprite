
split :: [Bool] -> ([Bool],[Bool])
split (x++y) = (x,y)
main = split [x,y,True] where x,y free