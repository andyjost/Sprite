data T = A | B | C
main = ((x =:= y & y =:= A) &> y) ? x where x,y free