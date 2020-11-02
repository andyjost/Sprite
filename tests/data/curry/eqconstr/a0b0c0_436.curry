data T = A | B | C
main = ((x =:= B & A =:= y & y =:= x) &> (x, y)) ? (x, y) where x,y free