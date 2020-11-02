data T = A | B | C
main = x ? ((y =:= x & y =:= B) &> x) ? y where x,y free