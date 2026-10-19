-- Free variables: narrowing finds them, rigid operations wait for them.
module Vars where

-- The last element, by a functional pattern.
last :: Data a => [a] -> a
last (_ ++ [x]) = x

-- Every way to split a list, by narrowing two free variables.
split :: Data a => [a] -> ([a], [a])
split zs | xs ++ ys =:= zs = (xs, ys)
  where xs, ys free
