last :: Prelude.Data a => [a] -> a
last (_++[x]) = x
main :: (Bool, Bool)
main = last [failed::(Bool,Bool), (failed::Bool, True)]
