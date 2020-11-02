data T = A | B | C
main = ((x =:= y & A =:= y) &> y) ? x ? y where x,y free