module Tools where

coin :: Int
coin = 0 ? 1

three :: Int
three = 3

nothing :: Int
nothing = failed

boom :: Int
boom = error "boom"

rule :: String -> [String] -> String
rule "a" ["x"]      = "cmd1"
rule "a" ["y", "z"] = "cmd2"

main :: Int
main = three
