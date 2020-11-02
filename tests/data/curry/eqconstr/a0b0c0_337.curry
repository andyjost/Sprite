data T = A | B | C
main = ((y =:= x & y =:= A & x =:= B) &> (x, y)) ? (x, y) where x,y free