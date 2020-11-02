data T = A T T | B T | C
main = (x =:= A (A x11 x12) (B x21    )) &> x where x,x11,x12,x21     free