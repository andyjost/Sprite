data T = A | B | C
main = ((y =:= x & x =:= B & y =:= A) &> (x, y)) ? (x, y) where x,y free