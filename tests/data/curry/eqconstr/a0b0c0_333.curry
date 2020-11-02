data T = A | B | C
main = ((x =:= y & A =:= y & A =:= x) &> (x, y)) ? (x, y) where x,y free