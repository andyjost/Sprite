data T = A | B | C
main = ((x =:= A & A =:= y & x =:= y) &> (x, y)) ? (x, y) where x,y free