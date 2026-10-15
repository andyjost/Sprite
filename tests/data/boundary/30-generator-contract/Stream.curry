module Stream where

three :: Int
three = 1 ? 2 ? 3

mixed :: Int
mixed = 1 ? error "boom" ? 2

nothing :: Int
nothing = failed
