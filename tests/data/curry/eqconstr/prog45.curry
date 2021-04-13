main :: Bool
main = ((x =:= x & y =:= y & x =:= y) &> x) ? x where x,y free