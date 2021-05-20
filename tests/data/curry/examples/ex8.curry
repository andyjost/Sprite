main :: (Bool, [Bool])
main = x =:= y &> (head x, y) where x, y free
