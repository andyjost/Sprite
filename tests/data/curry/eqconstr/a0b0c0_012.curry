data T = A | B | C
main = ((x =:= y & y =:= A) &> x) ? x where x,y free