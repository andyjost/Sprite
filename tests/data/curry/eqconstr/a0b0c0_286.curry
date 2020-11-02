data T = A | B | C
main = x ? ((y =:= x & B =:= y) &> y) ? y where x,y free