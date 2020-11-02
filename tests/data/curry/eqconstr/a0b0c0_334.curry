data T = A | B | C
main = ((x =:= y & A =:= y & B =:= x) &> (x, y)) ? (x, y) where x,y free