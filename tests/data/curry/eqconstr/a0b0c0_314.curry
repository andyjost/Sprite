data T = A | B | C
main = ((y =:= x & x =:= C & y =:= A) &> (x, y)) ? (x, y) where x,y free