-- Utilities to manipulate FlatCurry programs

module FlatManipLib where

import List
import FlatCurry.Types
import SetFunctions

-- subexpr e = (p,x) iff x is the subexpression of e at path p
subexpr :: Expr -> ([Int],Expr)
subexpr a = ([], a)
subexpr (Comb _ _ (x++[e]++_))
  = fix (length x) (subexpr e)
subexpr (Let (x++[(_,e)]++_) _)
  = fix (length x) (subexpr e)
subexpr (Let _ e)
  = fix (-1) (subexpr e)
subexpr (Free _ e)
  = fix 0 (subexpr e)
subexpr (Or e _)
  = fix 1 (subexpr e)
subexpr (Or _ e)
  = fix 2 (subexpr e)
subexpr (Case _ e _) 
  = fix (-1) (subexpr e)
subexpr (Case _ _ (x++[Branch _ e]++_))
  = fix (length x) (subexpr e)
subexpr (Typed e _)
  = fix 0 (subexpr e)
-- should function fix be a monad?
fix :: Int -> ([Int], Expr) -> ([Int], Expr)
fix p (ps, e) = (p:ps, e)

replace :: Expr -> [Int] -> Expr -> Expr
-- replace context path sub
replace _ [] s = s
replace (Comb ct qn (x++[e]++y)) (p:ps) s
  | p == length x 
  = Comb ct qn  (x++[replace e ps s]++y)
replace (Let (x++[(v,e)]++y) n) (p:ps) s
  | p == length x
  = Let (x++[(v,replace e ps s)]++y) n
replace (Let n e) (-1:ps) s
  = Let n (replace e ps s) 
replace (Free vs e) (0:ps) s
  = Free vs (replace e ps s)
replace (Or e n) (1:ps) s
  = Or (replace e ps s) n
replace (Or n e) (2:ps) s  
  = Or n (replace e ps s)
replace (Case ct e bs) (-1:ps) s
  = Case ct (replace e ps s) bs
replace (Case ct n (x++[Branch pt e]++y)) (p:ps) s
  | p == length x
  = Case ct n (x++[Branch pt (replace e ps s)]++y)
replace (Typed e t) (-1:ps) s
  = Typed (replace e ps s) t

with_Subexpr :: Expr -> Expr
with_Subexpr expr
  = expr
  ? (Comb _ _ (_ ++ [with_Subexpr expr] ++ _))
  ? (Let (_ ++ [(_, with_Subexpr expr)] ++ _) _)
  ? (Let _ (with_Subexpr expr))
  ? (Free _ (with_Subexpr expr))
  ? (Or (with_Subexpr expr) _)
  ? (Or _ (with_Subexpr expr))
  ? (Case _ _ (_ ++ [(Branch _ (with_Subexpr expr))] ++ _))
  ? (Case _ (with_Subexpr expr) _)
  ? (Typed (with_Subexpr expr) _)

-- all the variables referred to in an expression
refVarOf :: Expr -> Int
refVarOf (with_Subexpr (Var v)) = v
allRefVarOf :: Expr -> [Int]
allRefVarOf expr = nub (sortValues (set1 refVarOf expr))

-- all the variables declared in an expression
declVarOf :: Expr -> [Int]
declVarOf (with_Subexpr (Let vl _)) = map fst vl
declVarOf (with_Subexpr (Free vi _)) = vi
declVarOf (with_Subexpr (Case _ _ a@(Branch (Pattern _ _) _ : _)))
  = concatMap (\ (Branch (Pattern _ vl) _) -> vl) a
allDeclVarOf :: Expr -> [Int]
allDeclVarOf expr = nub (concat (sortValues (set1 declVarOf expr)))

unboundVarOf expr = allRefVarOf expr \\ allDeclVarOf expr
