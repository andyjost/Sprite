data T = A | B | C
main = ((y =:= x & C =:= x & A =:= y) &> (x, y)) ? (x, y) where x,y free