
data N = N1 | N2 | N3 | N4 | N5
insert :: N -> [N] -> [N]
insert a [] = [a]
insert a (b:bs) = a:b:bs
insert a (b:bs) = b: insert a bs
perm :: [N] -> [N]
perm [] = []
perm (a:as) = insert a (perm as)

main = perm [N1, N2, N3]