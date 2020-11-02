data T = A | B | C
main = ((y =:= x & y =:= A & x =:= A) &> (x, y)) ? (x, y) where x,y free