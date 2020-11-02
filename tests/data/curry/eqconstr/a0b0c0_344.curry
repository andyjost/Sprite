data T = A | B | C
main = ((y =:= x & y =:= A & C =:= x) &> (x, y)) ? (x, y) where x,y free