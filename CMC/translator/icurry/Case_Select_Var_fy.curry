{-# OPTIONS_CYMAKE -Wnone #-} -- no warnings
{-# OPTIONS_CYMAKE -F --pgmF=currypp --optF=defaultrules #-}

module Case_Select_Var_fy(execute) where

import Unsafe
import List(maximum)
import FlatCurry.Types
import FlatManipLib

-- Transform a case argument of a symbol application into a call to a
-- function, and define the corresponding function.

execute :: Prog -> Prog
execute  (Prog name imported_list data_list old_funct_list op_list)
--  | trace ( PPFlat.execute
--     (Prog name imported_list data_list old_funct_list op_list)
--     ++ "\n\n" ++ PPFlat.execute
--     ( Prog name imported_list data_list new_funct_list op_list)
--     ++ "\n" ) True
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
      fun_list -> loopFunct (fun_list++fs) (counter+2)

-- Transform all the functions of the program
-- "#B" is the trade mark
travFunct :: FuncDecl -> Int -> DET [FuncDecl]
travFunct (Func _ _ _ _ (External _)) _ = []
travFunct (Func qname arity visibility xtype (Rule var_list body)) counter
  = case redex_path body of
       Nothing -> []
       Just (p, redex@(Case ct selector br)) ->
         let
           -- all the variable appearing in the redex
	   all_vars = allRefVarOf redex
	   -- a fresh variable not in the redex or replacement
           new_var = if all_vars == [] then 1 else maximum all_vars + 1
           new_name = (fst qname, snd qname ++ "_#B" ++ show counter)
           new_body = Case ct (Var new_var) br
	   -- the variable that must be passed into the new function
	   -- these are the variable referenced, but not declared, in each branch
	   pass_vars = filter (/= new_var) (unboundVarOf new_body)
           call = Comb FuncCall new_name (selector : map Var pass_vars)
	   old_body = replace body p call
           old_funct = Func qname arity visibility xtype (Rule var_list old_body)
           new_funct = Func new_name (length pass_vars + 1) Private (TVar 0)
                            (Rule (new_var : pass_vars) new_body)
         in [old_funct, new_funct]

redex_path t
  | a == Case _ selector _
  && subexpr t == (p,  a)
  && is_not_var selector
  = Just (p, a)
  where is_not_var x = case x of {Var _ -> False; _ -> True}
        a, selector, p free

redex_path'default t = Nothing
