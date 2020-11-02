data T = A | B | C
main = ((y =:= x & x =:= A & y =:= A) &> (x, y)) ? (x, y) where x,y free