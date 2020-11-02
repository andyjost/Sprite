data T = A | B | C
main = ((B =:= x & A =:= y & x =:= y) &> (x, y)) ? (x, y) where x,y free