data T = A | B | C
main = x ? ((y =:= A & y =:= x ) &> y) ? y where x,y free