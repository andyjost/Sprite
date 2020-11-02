data T = A | B | C
main = x ? ((y =:= x & B =:= y) &> x) ? y where x,y free