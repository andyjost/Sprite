data T = A | B | C
main = ((y =:= x & y =:= A & x =:= C) &> (x, y)) ? (x, y) where x,y free