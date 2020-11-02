data T = A | B | C
main = ((x =:= y & A =:= y) &> x) ? y where x,y free