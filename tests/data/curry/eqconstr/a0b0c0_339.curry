data T = A | B | C
main = ((y =:= x & A =:= y & x =:= A) &> (x, y)) ? (x, y) where x,y free