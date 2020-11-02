data T = A | B | C
main = ((x =:= y & y =:= A & x =:= B) &> (x, y)) ? (x, y) where x,y free