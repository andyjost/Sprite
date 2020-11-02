data T = A | B | C
main = ((y =:= x & x =:= C & A =:= y) &> (x, y)) ? (x, y) where x,y free