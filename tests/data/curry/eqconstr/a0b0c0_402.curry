data T = A | B | C
main = ((y =:= A & A =:= x & x =:= y) &> (x, y)) ? (x, y) where x,y free