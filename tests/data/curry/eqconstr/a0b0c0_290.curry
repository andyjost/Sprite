data T = A | B | C
main = x ? ((y =:= C & x =:= y ) &> y) ? y where x,y free