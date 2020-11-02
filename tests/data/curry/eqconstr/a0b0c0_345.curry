data T = A | B | C
main = ((y =:= x & A =:= y & A =:= x) &> (x, y)) ? (x, y) where x,y free