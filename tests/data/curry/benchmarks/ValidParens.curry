-- Given a string containing just the characters '(' and ')', find the length
-- of the longest valid (well-formed) parentheses substring.

import Control.SetFunctions

tails [] = []
tails s@(_:as) = s ? tails as

len_valid_parens s = len s 0 1
    where len [] _ _ = 0
          len ('(':as) w n        = len as (w+1) (n+1)
          len (')':as) w n | w>0  = let rec = len as (w-1) (n+1) in
                                              if (w==1) then (n ? rec) else rec

longest_valid_parens = maxValue . set1 (len_valid_parens . tails)

main =  longest_valid_parens "()(()(((()()))())()))()))(()())(())(())))()))())" == 0
