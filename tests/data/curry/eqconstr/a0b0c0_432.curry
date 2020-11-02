data T = A | B | C
main = ((x =:= A & y =:= A & y =:= x) &> (x, y)) ? (x, y) where x,y free