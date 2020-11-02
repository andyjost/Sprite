data T = A | B | C
main = ((x =:= A & A =:= y & y =:= x) &> (x, y)) ? (x, y) where x,y free