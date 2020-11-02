data T = A | B | C
main = ((A =:= y & C =:= x & y =:= x) &> (x, y)) ? (x, y) where x,y free