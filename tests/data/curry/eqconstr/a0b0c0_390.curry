data T = A | B | C
main = ((A =:= x & y =:= x & y =:= A) &> (x, y)) ? (x, y) where x,y free