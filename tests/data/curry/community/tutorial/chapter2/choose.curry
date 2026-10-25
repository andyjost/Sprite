choose :: a -> a -> a
choose x y = x
choose x y = y

one23 :: Int
one23 = choose 1 (choose 2 3)

main :: Int
main = one23
