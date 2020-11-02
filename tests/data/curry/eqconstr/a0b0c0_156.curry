data T = A | B | C
main = ((x =:= y & y =:= A) &> x) ? y ? x where x,y free