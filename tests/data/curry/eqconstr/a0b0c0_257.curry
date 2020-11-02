data T = A | B | C
main = x ? ((x =:= y & C =:= y) &> x) ? y where x,y free