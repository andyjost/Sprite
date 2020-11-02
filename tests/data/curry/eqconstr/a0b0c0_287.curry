data T = A | B | C
main = x ? ((y =:= x & C =:= y) &> y) ? y where x,y free