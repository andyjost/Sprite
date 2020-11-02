data T = A | B | C
main = ((y =:= A & x =:= C & x =:= y) &> (x, y)) ? (x, y) where x,y free