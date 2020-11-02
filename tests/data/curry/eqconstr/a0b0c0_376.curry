data T = A | B | C
main = ((x =:= B & x =:= y & A =:= y) &> (x, y)) ? (x, y) where x,y free