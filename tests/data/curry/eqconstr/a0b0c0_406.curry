data T = A | B | C
main = ((A =:= y & B =:= x & x =:= y) &> (x, y)) ? (x, y) where x,y free