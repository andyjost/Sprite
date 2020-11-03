
split :: [Bool] -> ([Bool],[Bool])
split (x++y) = (x,y)
main = split [True,False,True]