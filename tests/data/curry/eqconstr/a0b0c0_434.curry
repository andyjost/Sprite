data T = A | B | C
main = ((x =:= C & y =:= A & y =:= x) &> (x, y)) ? (x, y) where x,y free