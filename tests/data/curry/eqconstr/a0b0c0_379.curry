data T = A | B | C
main = ((B =:= x & x =:= y & y =:= A) &> (x, y)) ? (x, y) where x,y free