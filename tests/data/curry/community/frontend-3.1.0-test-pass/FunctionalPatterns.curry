{-# LANGUAGE FunctionalPatterns #-}

f (v@[] ++ v@(x:xs)) = x:xs ++ v

g (id ((:) x xs)) = x:xs
h (id (x:xs)) = x:xs
