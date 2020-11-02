data T = A | B | C
main = x ? ((y =:= x & y =:= A) &> x) ? y where x,y free