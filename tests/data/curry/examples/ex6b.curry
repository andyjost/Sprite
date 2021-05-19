main :: (Bool, [Bool])
main = let u = (head x, x) in u ? (True, snd u) where x free
