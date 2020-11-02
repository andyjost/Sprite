data T = A | B | C
main = x ? ((x =:= y & A =:= y) &> y) ? y where x,y free