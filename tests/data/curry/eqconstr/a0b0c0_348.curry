data T = A | B | C
main = ((y =:= A & x =:= y & x =:= A) &> (x, y)) ? (x, y) where x,y free