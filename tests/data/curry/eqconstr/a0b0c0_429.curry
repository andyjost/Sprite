data T = A | B | C
main = ((A =:= x & A =:= y & x =:= y) &> (x, y)) ? (x, y) where x,y free