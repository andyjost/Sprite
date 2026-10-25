--------------------------------------------------------------------------------
--- Test operation for library Text.Show
--------------------------------------------------------------------------------

import Prelude hiding ( ShowS, showString )
import Text.Show
import Test.Prop

showStringIsString :: String -> Prop
showStringIsString s = showString s [] -=- s

showStringConcat :: String -> String -> Prop
showStringConcat s1 s2 = (showString s1 . showString s2) [] -=- s1++s2

--- Separate a list of `ShowS`
sep :: ShowS -> [ShowS] -> ShowS
sep _ []       = id
sep s xs@(_:_) = foldr1 (\ f g -> f . s . g) xs

--- Replicate a `ShowS` a given number of times
replicateS :: Int -> ShowS -> ShowS
replicateS n funcS
  | n <= 0    = id
  | otherwise = funcS . replicateS (n - 1) funcS

replicateSIsConRep :: Int -> String -> Prop
replicateSIsConRep n s =
  n>=0 ==> replicateS n (showString s) [] -=- concat (replicate n s)

--- Concatenate a list of `ShowS`
concatS :: [ShowS] -> ShowS
concatS []       = id
concatS xs@(_:_) = foldr1 (\ f g -> f . g) xs

concatSIsConcat :: [String] -> Prop
concatSIsConcat xs = concatS (map showString xs) [] -=- concat xs
