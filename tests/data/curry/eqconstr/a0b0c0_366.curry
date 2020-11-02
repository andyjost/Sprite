data T = A | B | C
main = ((y =:= A & y =:= x & A =:= x) &> (x, y)) ? (x, y) where x,y free