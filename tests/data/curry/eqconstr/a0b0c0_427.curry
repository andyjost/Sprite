data T = A | B | C
main = ((B =:= x & y =:= A & x =:= y) &> (x, y)) ? (x, y) where x,y free