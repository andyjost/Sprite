data T = A | B | C
main = ((y =:= x & A =:= y & B =:= x) &> (x, y)) ? (x, y) where x,y free