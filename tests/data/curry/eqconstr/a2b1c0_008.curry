data T = A T T | B T | C
main = (x =:= A (B x11    ) (A x21 x22)) &> x where x,x11,x21,x22     free