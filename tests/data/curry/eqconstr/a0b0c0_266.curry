data T = A | B | C
main = x ? ((y =:= C & x =:= y ) &> x) ? y where x,y free