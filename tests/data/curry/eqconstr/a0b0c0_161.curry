data T = A | B | C
main = ((x =:= y & C =:= y) &> x) ? y ? x where x,y free