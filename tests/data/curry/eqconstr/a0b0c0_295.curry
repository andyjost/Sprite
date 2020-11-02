data T = A | B | C
main = x ? ((y =:= B & y =:= x ) &> y) ? y where x,y free