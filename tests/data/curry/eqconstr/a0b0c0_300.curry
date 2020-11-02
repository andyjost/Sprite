data T = A | B | C
main = ((x =:= y & x =:= A & y =:= A) &> (x, y)) ? (x, y) where x,y free