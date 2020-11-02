data T = A | B | C
main = ((A =:= x & x =:= y & y =:= A) &> (x, y)) ? (x, y) where x,y free