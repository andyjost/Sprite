data T = A | B | C
main = ((x =:= y & A =:= y) &> x) ? x where x,y free