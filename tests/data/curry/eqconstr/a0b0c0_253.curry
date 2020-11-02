data T = A | B | C
main = x ? ((x =:= y & y =:= B) &> x) ? y where x,y free