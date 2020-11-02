data T = A | B | C
main = ((x =:= y & x =:= B & A =:= y) &> (x, y)) ? (x, y) where x,y free