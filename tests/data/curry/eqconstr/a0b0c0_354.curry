data T = A | B | C
main = ((y =:= A & x =:= y & A =:= x) &> (x, y)) ? (x, y) where x,y free