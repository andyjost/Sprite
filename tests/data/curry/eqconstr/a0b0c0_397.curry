data T = A | B | C
main = ((y =:= A & x =:= B & x =:= y) &> (x, y)) ? (x, y) where x,y free