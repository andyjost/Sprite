data T = A | B | C
main = ((A =:= x & y =:= x & A =:= y) &> (x, y)) ? (x, y) where x,y free