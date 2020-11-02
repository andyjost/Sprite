data T = A | B | C
main = ((x =:= B & y =:= x & A =:= y) &> (x, y)) ? (x, y) where x,y free