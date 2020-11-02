data T = A | B | C
main = ((x =:= y & A =:= x & A =:= y) &> (x, y)) ? (x, y) where x,y free