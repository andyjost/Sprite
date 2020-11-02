data T = A | B | C
main = ((x =:= y & A =:= y) &> y) ? y ? x where x,y free