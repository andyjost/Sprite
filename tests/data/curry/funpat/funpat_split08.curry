
split :: [Bool] -> ([Bool],[Bool])
split (x++y) = (x,y)
main = split [x,y] where x,y free