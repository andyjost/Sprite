data T = A | B | C
main = x ? ((x =:= y & A =:= y) &> x) ? y where x,y free