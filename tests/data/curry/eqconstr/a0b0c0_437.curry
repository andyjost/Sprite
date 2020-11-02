data T = A | B | C
main = ((x =:= C & A =:= y & y =:= x) &> (x, y)) ? (x, y) where x,y free