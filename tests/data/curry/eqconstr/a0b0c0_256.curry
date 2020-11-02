data T = A | B | C
main = x ? ((x =:= y & B =:= y) &> x) ? y where x,y free