-- Compute the last element in a list using append:

append []     ys = ys
append (x:xs) ys = x : append xs ys


last xs | append ys [x] =:= xs
        = x  where x,ys free

main :: Int
main = last [1..1000]
