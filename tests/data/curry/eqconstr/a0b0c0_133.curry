data T = A | B | C
main = ((x =:= y & y =:= B) &> y) ? x ? y where x,y free