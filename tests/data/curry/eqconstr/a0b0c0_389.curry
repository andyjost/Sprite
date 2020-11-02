data T = A | B | C
main = ((x =:= C & y =:= x & A =:= y) &> (x, y)) ? (x, y) where x,y free