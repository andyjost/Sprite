data T = A | B | C
main = x ? ((x =:= y & y =:= C) &> y) ? y where x,y free