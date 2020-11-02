data T = A | B | C
main = ((A =:= y & A =:= x & y =:= x) &> (x, y)) ? (x, y) where x,y free