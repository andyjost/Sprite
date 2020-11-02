data T = A | B | C
main = ((x =:= y & y =:= B) &> x) ? y where x,y free