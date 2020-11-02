data T = A | B | C
main = ((x =:= y & y =:= C) &> x) ? y where x,y free