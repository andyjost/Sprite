data T = A | B | C
main = ((x =:= y & A =:= y & x =:= C) &> (x, y)) ? (x, y) where x,y free