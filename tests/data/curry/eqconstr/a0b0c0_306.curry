data T = A | B | C
main = ((x =:= y & A =:= x & y =:= A) &> (x, y)) ? (x, y) where x,y free