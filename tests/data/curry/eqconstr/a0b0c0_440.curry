data T = A | B | C
main = ((C =:= x & y =:= A & y =:= x) &> (x, y)) ? (x, y) where x,y free