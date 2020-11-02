data T = A | B | C
main = ((y =:= x & A =:= y & x =:= B) &> (x, y)) ? (x, y) where x,y free