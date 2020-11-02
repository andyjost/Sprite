data T = A | B | C
main = x ? ((x =:= y & y =:= A) &> x) ? y where x,y free