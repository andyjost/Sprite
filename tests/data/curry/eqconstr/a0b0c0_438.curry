data T = A | B | C
main = ((A =:= x & y =:= A & y =:= x) &> (x, y)) ? (x, y) where x,y free