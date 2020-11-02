data T = A | B | C
main = x ? ((y =:= x & A =:= y) &> y) ? y where x,y free