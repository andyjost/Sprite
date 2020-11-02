data T = A | B | C
main = ((x =:= C & x =:= y & y =:= A) &> (x, y)) ? (x, y) where x,y free