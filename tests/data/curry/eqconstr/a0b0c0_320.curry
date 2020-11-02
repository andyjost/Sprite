data T = A | B | C
main = ((y =:= x & C =:= x & y =:= A) &> (x, y)) ? (x, y) where x,y free