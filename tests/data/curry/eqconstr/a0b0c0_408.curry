data T = A | B | C
main = ((y =:= A & x =:= A & y =:= x) &> (x, y)) ? (x, y) where x,y free