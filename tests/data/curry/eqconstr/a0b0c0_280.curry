data T = A | B | C
main = x ? ((x =:= y & B =:= y) &> y) ? y where x,y free