data T = A | B | C
main = ((y =:= A & x =:= C & y =:= x) &> (x, y)) ? (x, y) where x,y free