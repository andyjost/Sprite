module App where

inc :: Int -> Int
inc x = x + 1

-- A relation with one equation per rule, as the makefile of example 24 has.
rule :: String -> [String] -> String
rule "a" ["x"]      = "cmd1"
rule "a" ["y", "z"] = "cmd2"

-- Takes a relation as a value and applies it.
usesRel :: (String -> [String] -> String) -> String
usesRel r = r "a" ["y", "z"]
