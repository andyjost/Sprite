data T = A | B | C
main = x ? ((y =:= x & C =:= y) &> x) ? y where x,y free