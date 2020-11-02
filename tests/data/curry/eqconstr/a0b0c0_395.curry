data T = A | B | C
main = ((C =:= x & y =:= x & A =:= y) &> (x, y)) ? (x, y) where x,y free