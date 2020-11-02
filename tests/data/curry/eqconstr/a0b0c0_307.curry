data T = A | B | C
main = ((x =:= y & B =:= x & y =:= A) &> (x, y)) ? (x, y) where x,y free