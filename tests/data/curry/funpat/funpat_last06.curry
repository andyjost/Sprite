last :: Prelude.Data a => [a] -> a
last (xs++[x]) = x
main :: Bool
main = snd $ last [(failed::Bool, True)]
