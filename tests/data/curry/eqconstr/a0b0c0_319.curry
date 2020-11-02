data T = A | B | C
main = ((y =:= x & B =:= x & y =:= A) &> (x, y)) ? (x, y) where x,y free