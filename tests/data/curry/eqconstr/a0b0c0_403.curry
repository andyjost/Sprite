data T = A | B | C
main = ((y =:= A & B =:= x & x =:= y) &> (x, y)) ? (x, y) where x,y free