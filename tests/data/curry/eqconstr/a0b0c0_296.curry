data T = A | B | C
main = x ? ((y =:= C & y =:= x ) &> y) ? y where x,y free