data T = A | B | C
main = ((x =:= y & y =:= C) &> y) ? x where x,y free