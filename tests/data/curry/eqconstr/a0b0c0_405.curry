data T = A | B | C
main = ((A =:= y & A =:= x & x =:= y) &> (x, y)) ? (x, y) where x,y free