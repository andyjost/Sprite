data T = A | B | C
main = ((A =:= y & y =:= x & x =:= C) &> (x, y)) ? (x, y) where x,y free