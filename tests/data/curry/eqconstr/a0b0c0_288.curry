data T = A | B | C
main = x ? ((y =:= A & x =:= y ) &> y) ? y where x,y free