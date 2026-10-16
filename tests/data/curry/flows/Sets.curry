module Sets where
import Control.SetFunctions

coin :: Int
coin = 0 ? 1

rule :: String -> [String] -> String
rule "a" ["x"]      = "cmd1"
rule "a" ["y", "z"] = "cmd2"

inc :: Int -> Int
inc x = x + 1

nothing :: Int
nothing = failed

-- The choice is made outside the set function and captured by the lambda:
-- each value of x gives its own set (#117).
ord2 :: ([Int], Int)
ord2 = let x = 0 ? 1 in (sortValues (set1 (\y -> x + y) 10), x)

-- A set function inside the function of another.
nested :: [[Int]]
nested = sortValues (set1 (\n -> sortValues (set0 (n ? n + 1))) 0)

-- Two coins under one set function: four values, two of them equal.
twice :: [Int]
twice = sortValues (set0 (coin + coin))
