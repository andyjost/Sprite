data T = A | B | C
main = ((y =:= A & y =:= x & x =:= C) &> (x, y)) ? (x, y) where x,y free