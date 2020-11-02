data T = A | B | C
main = x ? ((y =:= x & y =:= C) &> x) ? y where x,y free