data T = A | B | C
main = ((x =:= C & y =:= A & x =:= y) &> (x, y)) ? (x, y) where x,y free