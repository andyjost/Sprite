module Util where

--member l | l =:= a ++ [b] ++ c = a where a, b, c free 
member (x:xs) = x ? member xs


zipWithIndex l = h l 0
         where h [] _ = []
               h (x:xs) i = (i, x) : h xs (i+1)
mapWithIndex f l = h l 0
         where h [] _ = []
               h (x:xs) i = f i x : h xs (i+1)


mkString sep [] = ""
mkString sep l@(_:_) = foldl1 (\acc x-> acc ++ sep ++ x) l

swap (a, b) = (b, a)
