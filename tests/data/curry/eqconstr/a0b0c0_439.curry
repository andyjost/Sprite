data T = A | B | C
main = ((B =:= x & y =:= A & y =:= x) &> (x, y)) ? (x, y) where x,y free