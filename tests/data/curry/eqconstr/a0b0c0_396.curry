data T = A | B | C
main = ((y =:= A & x =:= A & x =:= y) &> (x, y)) ? (x, y) where x,y free