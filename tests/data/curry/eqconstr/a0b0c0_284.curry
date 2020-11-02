data T = A | B | C
main = x ? ((y =:= x & y =:= C) &> y) ? y where x,y free