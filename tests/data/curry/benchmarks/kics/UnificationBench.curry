module UnificationBench where

import List (nub)

iff :: Bool -> a -> a
iff b x = if b then x else failed

---------------------------------------------------
-- Last
---------------------------------------------------

lastS  xs = ys ++ [y] =:= xs &> y where y, ys free

lastEq xs = iff (ys ++ [y] == xs) y where y, ys free

inc x n | n == 0    = x 
        | otherwise = 1 + inc (n - 1) x

goal_last_1S  = lastS  (take 100000 (repeat failed) ++ [1])
goal_last_1Eq = lastEq (take 100000 (repeat failed) ++ [1])


goal_last_2S  = lastS  (map (inc 0) [1..10000])
goal_last_2Eq = lastEq (map (inc 0) [1..10000])


---------------------------------------------------
-- lengthUpToRepeat
---------------------------------------------------




lengthUpToRepeatS xs = (p++[r]++q) =:= xs 
                       &> if nub p == p && elem r p 
                          then length p + 1
                          else failed
 where p, r, q free


goal_lUpToR_S = lengthUpToRepeatS ([1..50] ++ [1] ++ [51 ..])


---------------------------------------------------------------
-- grep
---------------------------------------------------------------

data RE a = Lit a
          | Alt  (RE a) (RE a)
          | Conc (RE a) (RE a)
          | Star (RE a)

-- My characters:

data Chr = A | B | C | D | E

-- Example: regular expression (ab*)

abstar = Conc (Lit A) (Star (Lit B))
-- Example: regular expression (ab*c)

abstarc = Conc abstar (Lit C)

-- Semantics of regular expressions

sem :: RE a -> [a]
sem (Lit c)    = [c]
sem (Alt  a b) = sem a ? sem b
sem (Conc a b) = sem a ++ sem b
sem (Star a)   = [] ? sem (Conc a (Star a))

grepS :: RE a -> [a] -> Success
grepS r s = xs ++ sem r ++ ys =:= s  where xs,ys free


biggrepS n =
  grepS abstarc (take n (concatMap (\i->A : take i (repeat B)) [1..]) ++ [A,B,C])
grepEq :: RE a -> [a] -> Success
grepEq r s = iff (xs ++ sem r ++ ys == s) success  where xs,ys free


biggrepEq n =
  grepEq abstarc (take n (concatMap (\i->A : take i (repeat B)) [1..]) ++ [A,B,C])

goal_grep_S  = biggrepS 50000
goal_grep_Eq = biggrepEq 50000

----------------------------------------------------------------------------
-- Half
----------------------------------------------------------------------------

data Peano = O | S Peano

toPeano :: Int -> Peano
toPeano n = if n==0 then O else S (toPeano (n-1))

fromPeano :: Peano -> Int
fromPeano O = 0
fromPeano (S p) = 1 + fromPeano p

add :: Peano -> Peano -> Peano
add O     p = p
add (S p) q = S (add p q)

halfEq y |  (add x x) == y = x where x free 
halfS  y | (add x x) =:= y = x where x free


goal_half_Eq = fromPeano (halfEq (toPeano 10000))
goal_half_S  = fromPeano (halfS  (toPeano 10000))


--------------------------------------------------------------
-- ExpVarFunPats
--------------------------------------------------------------

data Exp = Num Peano | Var VarName | Add Exp Exp | Mul Exp Exp

data VarName = X1 | X2 | X3
data Position = Lt | Rt

evalTo e = Add (Num O) e
         ? Add e (Num O)
         ? Mul (Num (S O)) e
         ? Mul e (Num (S O))

replace _         []    x = x
replace (Add l r) (Lt:p) x = Add (replace l p x) r
replace (Add l r) (Rt:p) x = Add l (replace r p x)
replace (Mul l r) (Lt:p) x = Mul (replace l p x) r
replace (Mul l r) (Rt:p) x = Mul l (replace r p x)

genExpWithVar n = if n==0 then Add (Var X1) (Num O)
                          else Mul (Num (S O)) (genExpWithVar (n-1))

genExpWithVar' n = if n==0 then Add (Var X1) (Num O)
                          else Mul (genExpWithVar' (n-1)) (Num (S O))

genExpWithVar'' n = gen n True
 where gen m var = case m of
         0 -> if var then Add (Var X1) (Num O) else Add (Num O) (Num O)
         _ -> let m1 = m - 1 in Mul (gen m1 False) (gen m1 var) 

-- return some variable occurring in an expression:

varInExpS :: Exp -> VarName
varInExpS exp = (replace x y (Var v)) =:= exp &> v where x, y, v free

varInExpEq :: Exp -> VarName
varInExpEq exp = iff (replace x y (Var v) == exp) v where x, y, v free

-- find a variable in an expression having 20003 nodes
goal_expVar_S  = varInExpS  (genExpWithVar 25000)
goal_expVar_Eq = varInExpEq (genExpWithVar 25000)

goal_expVar_S'  = varInExpS  (genExpWithVar' 100)
goal_expVar_Eq' = varInExpEq (genExpWithVar' 100)

goal_expVar_S''  = varInExpS  (genExpWithVar'' 14)
goal_expVar_Eq'' = varInExpEq (genExpWithVar'' 14)

----------------------------------------------------------------
-- Simplify
----------------------------------------------------------------

simplifyS :: Exp -> Exp
simplifyS exp = (replace c p (evalTo x)) =:= exp &> replace c p x
  where c, p, x free

simplifyEq :: Exp -> Exp
simplifyEq exp = iff (replace c p (evalTo x) == exp) (replace c p x)
  where c, p, x free

genExpWithMult1 n = if n==0 then Mul (Num (S O)) (Var X1)
                            else Mul (Num (S (S O))) (genExpWithMult1 (n-1))

expSize (Num _) = 1
expSize (Var _) = 1
expSize (Add e1 e2) = expSize e1 + expSize e2 + 1
expSize (Mul e1 e2) = expSize e1 + expSize e2 + 1

-- make a single simplifcation step in an expression having 4003 nodes
goal_simplify_S  = expSize (simplifyS  (genExpWithMult1 2000))
goal_simplify_Eq = expSize (simplifyEq (genExpWithMult1 2000))

----------------------------------------------------------------
-- Palindrom
----------------------------------------------------------------


paliS :: [a] -> Success
paliS ys = (xs ++ reverse xs)     =:= ys where xs free  
paliS ys = (xs ++ x : reverse xs) =:= ys where x, xs free

paliEq :: [a] -> Success
paliEq ys = iff (xs ++ reverse xs     == ys) success where xs free
paliEq ys = iff (xs ++ x : reverse xs == ys) success where x, xs free

longPali n = take n (repeat True) ++ take n (repeat False) ++ [False] ++
             take n (repeat False) ++ take n (repeat True)

goal_pali_S  = paliS  (longPali 1000)
goal_pali_Eq = paliEq (longPali 1000)

---------------------------------------------------------------------
-- HorseMan
---------------------------------------------------------------------

horsemanS m h heads feet =  
   heads =:= add m h  &  feet =:= add (add m m) (add (add h h) (add h h))

-- with Boolean equality:
horsemanEq m h heads feet =  
   heads == add m h  &&  feet == add (add m m) (add (add h h) (add h h))

-- How many men and horses have 800 heads and 2000 feet, result as int value:
goal_horseMan_S | horsemanS m h (toPeano 800) (toPeano 2000)
      = (fromPeano m,fromPeano h)  where m,h free

goal_horseMan_Eq | horsemanEq m h (toPeano 800) (toPeano 2000)
       = (fromPeano m,fromPeano h)  where m,h free
