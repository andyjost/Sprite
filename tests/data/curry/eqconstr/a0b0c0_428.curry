data T = A | B | C
main = ((C =:= x & y =:= A & x =:= y) &> (x, y)) ? (x, y) where x,y free