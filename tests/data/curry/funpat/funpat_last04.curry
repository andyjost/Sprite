last :: Prelude.Data a => [a] -> a
last (_++[x]) = x
main :: Bool
main = snd $ last [failed::(Bool,Bool), (failed::Bool, True)]
