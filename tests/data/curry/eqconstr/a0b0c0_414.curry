data T = A | B | C
main = ((y =:= A & A =:= x & y =:= x) &> (x, y)) ? (x, y) where x,y free