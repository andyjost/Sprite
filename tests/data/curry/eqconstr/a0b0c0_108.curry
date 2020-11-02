data T = A | B | C
main = ((x =:= y & y =:= A) &> x) ? x ? y where x,y free