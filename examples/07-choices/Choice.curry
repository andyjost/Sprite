module Choice where

coin :: Int
coin = 0 ? 1

inc :: Int -> Int
inc x = x + 1

adder :: Int -> (Int -> Int)
adder x = (+) x
