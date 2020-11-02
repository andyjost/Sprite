data T = A | B | C
main = x ? ((x =:= y & y =:= A) &> y) ? y where x,y free