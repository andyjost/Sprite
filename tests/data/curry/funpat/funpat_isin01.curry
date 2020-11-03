
data N = N1 | N2 | N3 | N4 | N5
isin :: N -> [N] -> Bool
isin x (_++[x]++_) = True
main = N1 `isin` [N1]