data T = A | B | C
main = ((x =:= B & A =:= y & x =:= y) &> (x, y)) ? (x, y) where x,y free