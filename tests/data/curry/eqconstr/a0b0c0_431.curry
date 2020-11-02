data T = A | B | C
main = ((C =:= x & A =:= y & x =:= y) &> (x, y)) ? (x, y) where x,y free