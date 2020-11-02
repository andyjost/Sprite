data T = A | B | C
main = x ? ((y =:= B & x =:= y ) &> y) ? y where x,y free