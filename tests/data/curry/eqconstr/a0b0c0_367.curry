data T = A | B | C
main = ((y =:= A & y =:= x & B =:= x) &> (x, y)) ? (x, y) where x,y free