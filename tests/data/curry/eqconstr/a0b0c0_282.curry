data T = A | B | C
main = x ? ((y =:= x & y =:= A) &> y) ? y where x,y free