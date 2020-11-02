data T = A | B | C
main = ((y =:= x & B =:= x & A =:= y) &> (x, y)) ? (x, y) where x,y free