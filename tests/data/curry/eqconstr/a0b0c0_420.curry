data T = A | B | C
main = ((x =:= A & y =:= A & x =:= y) &> (x, y)) ? (x, y) where x,y free