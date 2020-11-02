data T = A | B | C
main = ((x =:= y & x =:= C & y =:= A) &> (x, y)) ? (x, y) where x,y free