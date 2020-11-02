data T = A | B | C
main = ((x =:= B & x =:= y & y =:= A) &> (x, y)) ? (x, y) where x,y free