module Locals where
goal :: Int
goal = let x = y + 1 in x + x where y free
