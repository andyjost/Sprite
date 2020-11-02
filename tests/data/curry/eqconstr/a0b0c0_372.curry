data T = A | B | C
main = ((x =:= A & x =:= y & y =:= A) &> (x, y)) ? (x, y) where x,y free