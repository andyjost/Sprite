data T = A | B | C
main = ((x =:= y & y =:= B) &> x) ? x ? y where x,y free