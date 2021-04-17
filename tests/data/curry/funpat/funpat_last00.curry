last :: Prelude.Data a => [a] -> a
last (_++[x]) = x
main :: ()
main = last []
