data T = A | B | C
main = x ? ((x =:= y & y =:= B) &> y) ? y where x,y free