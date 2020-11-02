data T = A | B | C
main = ((x =:= A & y =:= x & A =:= y) &> (x, y)) ? (x, y) where x,y free