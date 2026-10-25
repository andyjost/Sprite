type Graph a = a -> a

succ :: Graph Int
succ 1 = 2
succ 1 = 3
succ 2 = 4
succ 3 = 4
succ 4 = 5
succ 5 = 6
succ 2 = 5
succ 3 = 2
succ 2 = 7
succ 4 = 7
succ 5 = 8
succ 9 = 10
succ 9 = 3
succ 10 = 12
succ 11 = 14
succ 12 = 13
succ 13 = 15
succ 14 = 12
succ 13 = 11
succ 15 = 9
succ 12 = 14
succ 11 = 8
succ 14 = 9

inv :: Graph a -> Graph a
inv g a | a =:= g b = b where b free

undir :: Graph a -> Graph a
undir g a = g a
undir g a = inv g a

path :: Graph a -> a -> a -> [a]
path = path' [] where
  path' :: [a] -> Graph a -> a -> a -> [a]
  path' p g a b | a == b          = reverse (a:p)
                | (a `notElem` p) = path' (a:p) g (g a) b

main = length (path (undir succ) 1 15)
