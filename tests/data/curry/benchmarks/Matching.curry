-- Given an input string (s) and a pattern (p), implement wildcard pattern
-- matching with support for '?' and '*' where:
--
--     '?' Matches any single character.
--     '*' Matches any sequence of characters (including the empty sequence).
--
-- The matching should cover the entire input string (not partial).

import Control.SetFunctions

tails [] = []
tails s@(_:as) = s ? tails as

match :: String -> String -> Bool
match s p = notEmpty $ (set2 aux) s p
    where aux [] [] = True
          aux (x:as) (x:bs) | x /= '?' && x /= '*' = aux as bs
          aux (_:as) ('?':bs) = aux as bs
          aux as ('*':bs) = aux (tails as) bs

main :: Bool
main =  match "aa"     "a"     == False
     && match "aa"     "*"     == True
     && match "abc"    "a*"    == True
     && match "abc"    "a?"    == False
     && match "cb"     "?a"    == False
     && match "adceb"  "a*b"   == True
     && match "acdcb"  "a*c?b" == False
     && match "acdcb"  "a*cb"  == True
     && match "acdbb"  "a*c?b"  == False
     && match "acdbcccb"  "a*c?b"  == True
     && match "aaaaaaaaaabbbbbbbbbb"  "a*a*a*a*a*b*b*b*b*b"  == True
