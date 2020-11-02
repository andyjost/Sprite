data T = A | B | C
main = ((y =:= x & A =:= y & x =:= C) &> (x, y)) ? (x, y) where x,y free