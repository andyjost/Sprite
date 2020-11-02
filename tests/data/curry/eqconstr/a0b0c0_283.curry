data T = A | B | C
main = x ? ((y =:= x & y =:= B) &> y) ? y where x,y free