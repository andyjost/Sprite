data T = A | B | C
main = ((x =:= y & A =:= y & x =:= B) &> (x, y)) ? (x, y) where x,y free