-- Higher-order insertion sort:
sort :: (a -> a -> Bool) -> [a] -> [a]
sort _ []     = []
sort f (x:xs) = insert f x (sort f xs)

insert :: (a -> a -> Bool) -> a -> [a] -> [a]
insert _ x [] = [x]
insert f x (y:ys) | f x y    = x:y:ys
                  | otherwise = y : insert f x ys

-- sort grades with lexicographic ordering:
sortClassesE xs = sort lex xs
   where lex (x,y) (u,v) = x<u || x==u && ord y <= ord v 

-- the same more compact with an anonymous function:
sortClassesA xs = sort (\(x,y) (u,v) -> x<u || x==u && ord y <= ord v) xs


main = sortClassesA [(2,'c'),(1,'b'),(2,'a')]