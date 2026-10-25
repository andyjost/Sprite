module ACVisibility (T(..), Array, f') where

data T = T

data Array b = Array (Int -> b) (Entry b)

data Entry b = Entry b (Entry b) (Entry b) | Empty

f' :: [a] -> [a]
f' xs = g' (reverse xs)
 where
  g' ys = xs ++ ys
