data T = A | B | C
main = ((y =:= A & y =:= x & x =:= B) &> (x, y)) ? (x, y) where x,y free