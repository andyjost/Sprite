data T = A | B | C
main = ((x =:= y & y =:= C) &> y) ? x ? y where x,y free