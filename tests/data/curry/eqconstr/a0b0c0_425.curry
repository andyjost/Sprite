data T = A | B | C
main = ((x =:= C & A =:= y & x =:= y) &> (x, y)) ? (x, y) where x,y free