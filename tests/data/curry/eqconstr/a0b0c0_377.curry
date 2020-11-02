data T = A | B | C
main = ((x =:= C & x =:= y & A =:= y) &> (x, y)) ? (x, y) where x,y free