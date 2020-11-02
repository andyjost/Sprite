data T = A | B | C
main = ((C =:= x & x =:= y & y =:= A) &> (x, y)) ? (x, y) where x,y free