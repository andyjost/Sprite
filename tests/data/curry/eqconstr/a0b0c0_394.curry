data T = A | B | C
main = ((B =:= x & y =:= x & A =:= y) &> (x, y)) ? (x, y) where x,y free