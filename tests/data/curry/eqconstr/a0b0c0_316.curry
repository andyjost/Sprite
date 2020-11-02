data T = A | B | C
main = ((y =:= x & x =:= B & A =:= y) &> (x, y)) ? (x, y) where x,y free