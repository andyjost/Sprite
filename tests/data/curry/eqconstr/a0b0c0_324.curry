data T = A | B | C
main = ((x =:= y & y =:= A & x =:= A) &> (x, y)) ? (x, y) where x,y free