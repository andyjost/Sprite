data T = A | B | C
main = ((A =:= y & y =:= x & C =:= x) &> (x, y)) ? (x, y) where x,y free