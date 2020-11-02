data T = A | B | C
main = ((x =:= y & B =:= y) &> x) ? x ? y where x,y free