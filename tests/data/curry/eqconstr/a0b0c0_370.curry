data T = A | B | C
main = ((A =:= y & y =:= x & B =:= x) &> (x, y)) ? (x, y) where x,y free