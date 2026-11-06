module ContractChoice where

import Control.Search.SetFunctions (selectValue, set1)
import System.IO.Unsafe (trace)

prefix :: [Int] -> [Int]
prefix (xs ++ [_]) = check xs

check :: [Int] -> [Int]
check xs = if null xs then xs else trace "unreachable" xs

main :: IO ()
main = print (selectValue (set1 prefix [1]))

value :: [Int]
value = selectValue (set1 prefix [1])
