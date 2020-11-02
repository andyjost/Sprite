data T = A | B | C
main = ((x =:= y & y =:= A & C =:= x) &> (x, y)) ? (x, y) where x,y free