data T = A | B | C
main = ((y =:= A & x =:= y & B =:= x) &> (x, y)) ? (x, y) where x,y free