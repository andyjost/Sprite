data T = A | B | C
main = ((x =:= y & C =:= y) &> x) ? x ? y where x,y free