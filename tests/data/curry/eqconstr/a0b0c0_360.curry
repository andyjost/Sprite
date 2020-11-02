data T = A | B | C
main = ((y =:= A & y =:= x & x =:= A) &> (x, y)) ? (x, y) where x,y free