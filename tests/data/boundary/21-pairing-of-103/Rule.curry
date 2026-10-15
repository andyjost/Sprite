module Rule where

rule :: String -> [String] -> String
rule "a" ["x"]      = "cmd1"
rule "a" ["y", "z"] = "cmd2"

rulePair :: String -> [String] -> (String, [String])
rulePair s ins = (rule s ins, ins)
