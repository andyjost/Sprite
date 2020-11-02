data T = A | B | C
main = ((y =:= A & x =:= y & C =:= x) &> (x, y)) ? (x, y) where x,y free