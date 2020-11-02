data T = A | B | C
main = ((y =:= x & A =:= y & C =:= x) &> (x, y)) ? (x, y) where x,y free