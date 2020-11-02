data T = A | B | C
main = ((B =:= x & A =:= y & y =:= x) &> (x, y)) ? (x, y) where x,y free