data T = A | B | C
main = ((x =:= C & y =:= x & y =:= A) &> (x, y)) ? (x, y) where x,y free