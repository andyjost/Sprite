data T = A | B | C
main = ((x =:= y & y =:= C) &> x) ? x ? y where x,y free