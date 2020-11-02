data T = A | B | C
main = ((x =:= B & y =:= x & y =:= A) &> (x, y)) ? (x, y) where x,y free