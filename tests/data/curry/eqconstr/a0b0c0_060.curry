data T = A | B | C
main = ((x =:= y & y =:= A) &> x) ? y where x,y free