data T = A | B | C
main = ((A =:= x & x =:= y & A =:= y) &> (x, y)) ? (x, y) where x,y free