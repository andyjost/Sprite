data T = A | B | C
main = ((x =:= y & y =:= C) &> x) ? y ? x where x,y free