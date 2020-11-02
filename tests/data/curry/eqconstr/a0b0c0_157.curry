data T = A | B | C
main = ((x =:= y & y =:= B) &> x) ? y ? x where x,y free