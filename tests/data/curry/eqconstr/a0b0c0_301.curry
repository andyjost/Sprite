data T = A | B | C
main = ((x =:= y & x =:= B & y =:= A) &> (x, y)) ? (x, y) where x,y free