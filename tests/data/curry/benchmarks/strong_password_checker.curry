{- A password is considered strong if the below conditions are all met:

    * It has at least 6 characters and at most 20 characters.
    * It contains at least one lowercase letter, at least one uppercase letter,
      and at least one digit.
    * It does not contain three repeating characters in a row (i.e.,
      "...aaa..." is weak, but "...aa...a..." is strong, assuming other
      conditions are met).

Given a string `password`, return the minimum number of steps required to make
`password` strong. if password is already strong, return 0.

In one step, you can:

    * Insert one character to password,
    * Delete one character from password, or
    * Replace one character of password with another character.
-}

{-# OPTIONS_CYMAKE -F --pgmF=currypp --optF=defaultrules #-}

import Control.SetFunctions
import Data.List

lower = [chr n | n <- [ord 'a' .. ord 'z']]
upper = [chr n | n <- [ord 'A' .. ord 'Z']]
digit = [chr n | n <- [ord '0' .. ord '9']]
hasUpper pw = any (\x -> ord x >= ord 'A' && ord x <= ord 'Z') pw
hasLower pw = any (\x -> ord x >= ord 'a' && ord x <= ord 'z') pw
hasDigit pw = any (\x -> ord x >= ord '0' && ord x <= ord '9') pw
hasThreepeat (_++[x,x,x]++_) = True
hasThreepeat'default _ = False

data Step = INSERT | DELETE | REPLACE
step pw = let len = length pw in
              if length pw < 6 then INSERT else
              if length pw > 20 then DELETE else
              if not (hasLower pw && hasUpper pw && hasDigit pw)
                then REPLACE else
              if hasThreepeat pw then REPLACE else
              failed

score pw = (if hasUpper pw then 1 else 0)
         + (if hasLower pw then 1 else 0)
         + (if hasDigit pw then 1 else 0)
           {- Length penalty. -}
         - (let len = length pw in maximum [6 - len, len - 20, 0])
           {- Repetition penalty. -}
         - penalty pw

penalty pw = selectValue $ set1 penalty'aux pw
-- The aux function, which uses a default rule, must occur at file scope.
penalty'aux (b++[x,x,x]++e) = 1 + penalty (b++[x,x]++e)
penalty'aux'default _ = 0

byscore a b = compare (score a) (score b)

applystep s pw = maxValueBy byscore $ (set1 (dostep s)) pw
    where dostep INSERT pw' = insert (anyPos pw') (anyChar pw') pw'
          dostep DELETE pw' = delete (anyPos pw') pw'
          dostep REPLACE pw' = replace (anyPos pw') (anyChar pw') pw'
          insert n c ps@(p:pw') | n==0      = c:ps
                                | otherwise = p: insert (n-1) c pw'
          delete n (p:pw')      | n==0      = pw'
                                | otherwise = p: delete (n-1) pw'
          replace n c (p:pw')   | n==0 = c: pw'
                                | otherwise = p: replace (n-1) c pw'
          anyPos pw' = anyOf [0..length pw']
          anyChar pw' = anyOf [new vset pw' | vset <- [lower, upper, digit]]
          new valueset avoid = head $ filter (`notElem` avoid) valueset

fix pw | score pw /= 3 = let s = step pw
                             pw' = applystep s pw
                             (ss, pw'') = fix pw' in ((s:ss), pw'')
       | otherwise = ([], pw)

nsteps pw = let (ss, _) = fix pw in length ss

main =  nsteps "a"        == 5
     && nsteps "aA1"      == 3
     && nsteps "1337C0d3" == 0
     && nsteps "ABABABABABABABABABAB1" == 2
     && nsteps "AbABABABABABABABABAB1" == 1
     && nsteps "aaaBB"    == 1
     && nsteps "AAABB"    == 2
     && nsteps "AAAAAAAAAAAAAA" == 4
