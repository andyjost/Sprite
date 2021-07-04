-- Given a string s, find the length of the longest substring without repeating characters.
import Control.SetFunctions

tails [] = []
tails s@(_:as) = s ? tails as

subseqlen [] = 0
subseqlen (a:as) = 1 + subseqlen (takeWhile (/=a) as)

longest :: [Char] -> Int
longest = maxValue . set1 (subseqlen . tails)

main =  longest "abcabcbb" == 3
     && longest "bbbbb" == 1
     && longest "pwwkew" == 3
     && longest "" == 0

