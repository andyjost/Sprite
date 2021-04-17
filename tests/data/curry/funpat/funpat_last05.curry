last :: Prelude.Data a => [a] -> a
last (_++[x]) = x
main :: Bool
main = fst $ last [failed::(Bool,Bool), (True, failed::Bool)]
