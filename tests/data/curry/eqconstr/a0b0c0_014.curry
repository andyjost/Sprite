data T = A | B | C
main = ((x =:= y & y =:= C) &> x) ? x where x,y free