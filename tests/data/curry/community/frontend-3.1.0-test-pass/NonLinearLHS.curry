{-# LANGUAGE FunctionalPatterns #-}

double x x = True

multi x y y x = x + y

nested (x:x:_) x = x

funpat (n + n) (n + n) = n

combined ~(v:_) v = v

guarded x | x == x = x

leftB a b (_ ++ [a,b] ++ _) = success

f x (_ ++ [x]) [x] | not x = x

test [x] (x ++ x) (x ++ x) x | null x = x
