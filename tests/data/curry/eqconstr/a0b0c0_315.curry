data T = A | B | C
main = ((y =:= x & x =:= A & A =:= y) &> (x, y)) ? (x, y) where x,y free