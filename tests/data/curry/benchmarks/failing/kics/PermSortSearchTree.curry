import SearchTree

insert x [] = [x]
insert x (y:ys) = x:y:ys ? y : (insert x ys)

perm [] = []
perm (x:xs) = insert x (perm xs)

sorted :: [Int] -> [Int]
sorted []       = []
sorted [x]      = [x]
sorted (x:y:ys) | x <= y = x : sorted (y:ys)

psort xs = sorted (perm xs)

sortmain n = psort (2:[n,n-1 .. 3]++[1])

mainsort = sortmain 13

goal n = getSearchTree (sortmain n) >>= return . allValuesDFS

maintree = goal 13

-- print search tree for perm or permsort:
prpermst n = getSearchTree (perm [1..n]) >>= putStrLn . showSearchTree 
prsortst n = getSearchTree (psort [n,n-1 .. 1]) >>= putStrLn  . showSearchTree

