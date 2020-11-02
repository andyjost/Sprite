data T = A | B | C
main = ((x =:= y & A =:= y) &> x) ? y ? x where x,y free