data T = A | B | C
main = ((A =:= y & y =:= x & x =:= B) &> (x, y)) ? (x, y) where x,y free