data T = A | B | C
main = ((B =:= x & x =:= y & A =:= y) &> (x, y)) ? (x, y) where x,y free