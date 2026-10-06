-- Programs for unit_funpat_free_argument.py: the functions of FunPatFreeArg
-- read through set functions.  The free variable is created inside the
-- function of the set, so the value of the set carries it bound.

import Control.SetFunctions
import FunPatFreeArg

candidates :: (String -> [String] -> String) -> String -> [([String], String)]
candidates f t = sortValues (set2 cand f t)

countS :: [Int] -> [([Int], String)]
countS xs = sortValues (set1 countC xs)

wrapS :: Int -> [(Maybe Int, String)]
wrapS n = sortValues (set1 wrapC n)

doubleS :: Shape -> [(Shape, String)]
doubleS s = sortValues (set1 doubleC s)

upperS :: String -> [(Char, String)]
upperS s = sortValues (set1 upperC s)

singleS :: [(Maybe Int, String)]
singleS = sortValues (set0 singleC)

halfS :: Int -> [(Float, String)]
halfS n = sortValues (set1 halfC n)
