-- The penalty of a string is calculated as the number of times a character
-- occurs three times in a row.  For example, the penalty of "aaaa" is two, while
-- the penalty of "aabaa" is zero.
--
-- This file contains two implementations involving set functions.  The
-- challenge when doing so is to avoid factorial complexity, which requires
-- application of selectValue.

{-# OPTIONS_CYMAKE -F --pgmF=currypp --optF=defaultrules #-}
import Control.SetFunctions

------ penalty1 ------
-- Applies selectValue once.  Compelxity may depend on the search strategy.
penalty1 pw = selectValue $ set1 aux1 pw
aux1 (b++[x,x,x]++e) = 1 + aux1 (b++[x,x]++e)
aux1'default _ = 0

------ penalty2 ------
-- Applies selectValue at each iteration.  Complexity should not depend on the
-- search strategy.
penalty2 pw = selectValue $ set1 aux2 pw
aux2 (b++[x,x,x]++e) = 1 + penalty2 (b++[x,x]++e)
aux2'default _ = 0


main =  penalty1 "aaaa" == 2
     && penalty2 "aaaa" == 2
     && penalty1 "aabaa" == 0
     && penalty2 "aabaa" == 0
     && penalty1 "aaaabaaabbbb" == 5
     && penalty2 "aaaabaaabbbb" == 5
     && penalty1 "aaaaaaaaaaaaaaaaaaaa" == 18
     && penalty2 "aaaaaaaaaaaaaaaaaaaa" == 18

