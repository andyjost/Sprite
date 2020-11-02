data T = A | B | C
main = ((x =:= y & y =:= B) &> x) ? x where x,y free