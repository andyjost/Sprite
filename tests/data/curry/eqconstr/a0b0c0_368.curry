data T = A | B | C
main = ((y =:= A & y =:= x & C =:= x) &> (x, y)) ? (x, y) where x,y free