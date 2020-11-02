data T = A | B | C
main = ((x =:= y & B =:= y) &> x) ? y ? x where x,y free