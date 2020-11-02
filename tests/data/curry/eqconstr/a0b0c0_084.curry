data T = A | B | C
main = ((x =:= y & y =:= A) &> y) ? y where x,y free