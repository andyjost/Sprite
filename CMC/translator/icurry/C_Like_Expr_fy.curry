{-# OPTIONS_CYMAKE -F --pgmF=currypp --optF=defaultrules #-}

module C_Like_Expr_fy(execute) where

import FlatCurry.Types
import FlatManipLib
import Unsafe

-- Transform non C-like FlatCurry expressions
-- into C-like FlatCurry expressions.
-- Only the function list of a module is modified
execute :: Prog -> Prog
execute  (Prog name imported_list data_list old_funct_list op_list)
  =       Prog name imported_list data_list new_funct_list op_list
  where new_funct_list = loopFunct old_funct_list 0

-- loop over each function and transform it if necessary
-- the tranformation may create new functions (satellites)
-- use a counter to create new name for the new functions
loopFunct :: [FuncDecl] -> Int -> [FuncDecl]
loopFunct [] _ = []
loopFunct (f : fs) counter 
  = case travFunct f counter of
      [] -> f : loopFunct fs counter
      fun_list -> loopFunct (fun_list++fs) (counter+1)

-- "#A" is the trade mark
travFunct :: FuncDecl -> Int -> [FuncDecl]
travFunct (Func _ _ _ _ (External _)) _ = []
travFunct (Func qname arity visibility xtype (Rule var_list body)) counter
  -- | trace ("IN  " ++ show a ++ "\nOUT " ++ show result) True
  = result
  where
     (path,redex) = redex_path body
     new_var_list = unboundVarOf redex
     new_name = (fst qname, snd qname ++ "_#A" ++ show counter)
     call = Comb FuncCall new_name (map Var new_var_list)
     new_body = replace body path call
     result
       | path == [] = []
       | otherwise  = [ Func qname arity visibility xtype
		             (Rule var_list new_body)
                      , Func new_name (length new_var_list) Private (TVar 0)
			     (Rule new_var_list redex) ]
{-

We find expressions that must be replaced by function calls using
functional patterns.  These are the patterns:

Let-block and case-construct somewhere in the argument of a function application
  Note: could a non-cyclic let-block be avoided ???

Let-block and case-construct somewhere in the argument of an Or-construct

-}

redex_path :: Expr -> DET ([Int], Expr)

-- "let" and "case" as argument of "or"

redex_path t 
  |  subexpr t == (p, Or u _)
  && a == (Let _ _ ? Case _ _ _ ? Free _ _)
  && subexpr u == (q, a)
  = (p ++ [1] ++ q, a)
  where p,q,u,a free

redex_path t 
  |  subexpr t == (p, Or _ u)
  && a == (Let _ _ ? Case _ _ _ ? Free _ _)
  && subexpr u == (q, a)
  = (p ++ [2] ++ q, a)
  where p,q,u,a free

-- "let" and "case" as argument of a symbol application

redex_path t
  |  subexpr t == (p, Comb _ _ (x ++ [u] ++ _))
  && a == (Let _ _ ? Case _ _ _ ? Free _ _) 
  && subexpr u == (q, a)
  = (p ++ [length x] ++ q, a)
  where p,q,x,u,a free

-- "let" and "case" as argument of a "let" binding

redex_path t
  |  subexpr t == (p, Let (x ++ [(v,u)] ++ _) _)
  && a == (Let _ _ ? Case _ _ _)
  && subexpr u == (q, a)
  = (p ++ [length x] ++ q, a)
  where p,q,x,v,u,a free

-- "let" and "case" as argument of a "let" result

redex_path t
  |  subexpr t == (p, Let _ u)
  && a == (Let _ _ ? Case _ _ _ ? Free _ _)
  && subexpr u == (q, a)
  = (p ++ [-1] ++ q, a)
  where p,q,u,a free

-- "let" and "case" as argument of a "case" selector

redex_path t
  |  subexpr t == (p, Case _ u _)
  && a == (Let _ _ ? Case _ _ _ ? Free _ _)
  && subexpr u == (q, a)
  = (p ++ [-1] ++ q, a)
  where p,q,u,a free

-- "let" and "case" as argument of a "case" branch

redex_path t
  |  subexpr t == (p, Case _ _ (x++[Branch _ u]++_))
  && a == (Let _ _ ? Case _ _ _ ? Free _ _)
  && subexpr u == (q, a)
  = (p ++ [length x] ++ q, a)
  where p,q,x,u,a free

redex_path'default t = ([],t)
