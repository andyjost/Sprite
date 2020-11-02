data T = A | B | C
main = ((x =:= A & x =:= y & A =:= y) &> (x, y)) ? (x, y) where x,y free