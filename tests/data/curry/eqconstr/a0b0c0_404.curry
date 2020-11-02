data T = A | B | C
main = ((y =:= A & C =:= x & x =:= y) &> (x, y)) ? (x, y) where x,y free