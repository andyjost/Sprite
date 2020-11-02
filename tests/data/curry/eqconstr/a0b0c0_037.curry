data T = A | B | C
main = ((x =:= y & y =:= B) &> y) ? x where x,y free