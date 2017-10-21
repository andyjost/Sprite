-- {-# OPTIONS_CYMAKE -Wnone #-} -- no warnings
{-# OPTIONS_CYMAKE -F --pgmF=currypp --optF=defaultrules #-}

module RemoveInnerCases(execute) where

import Unsafe
import List
import FlatCurry.Types

-- Transform a case argument of a symbol application into a call to a
-- function, and define the corresponding function.

execute :: Prog -> DET Prog
execute a@(Prog qname imports types functs ops)
  -- | trace ("\nIN\n" ++ show a) True &&
  --   trace ("\nOUT\n" ++ show res) True
  = res
  where res = Prog qname imports types (trans_list functs) ops

-- Transform all the functions of the program
trans_list :: [FuncDecl] -> [FuncDecl]
trans_list [] = []
trans_list (a@(Func _ _ _ _ (External _)) : tl) = a : trans_list tl
trans_list (a@(Func _ _ _ _ (Rule _ _)) : tl)
  = adjusted : trans_list (new_functs ++ tl)
  where
    (adjusted : new_functs) = trans_one 1 [a]

-- Transform one function.  A case replacement in a function f
-- produces another function g.  Apply replacements to f as long as they
-- are needed, then move to the remaining functions.
--
-- There are many transformation.  Find if one is applicable.
-- If yes apply it, otherwise find if another is applicable.
-- If no transformation is applicable, we are done
trans_one :: Int -> [FuncDecl] -> [FuncDecl]
trans_one _ []
  -- | trace ("\ntrans_one done") True
  = []
trans_one counter a@(Func _ _ _ _ (Rule _ expr) : _)
  -- | trace ("\ntrans_one " ++ show (counter, a)) True
  = case find_under_wrapper False expr [] of
      Just path -> trans_one (counter+1) (transform_nested path counter a)
      Nothing -> case find_case_nonvar_select expr of
         Just path -> trans_one (counter+1) (transform_nonvar path counter a)
         Nothing -> a

transform_nested path counter
    (Func qname arity visibility typeexpr a@(Rule varindexlist expr) : tl)
  -- | trace "\n--- transform_nested ---" True
  --   && trace ("\n path " ++ show (path,expr)) True    
  --   && trace ("\n xcase " ++ show xcase) True    
  --   && trace ("\n var_list " ++ show var_list) True
  --   && trace ("\n new_args " ++ show new_args) True
  --   && trace ("\n new_name " ++ show new_name) True
  --   && trace ("\n new_function " ++ show new_function) True
  --   && trace ("\n new_expr " ++ show new_expr) True
  --   && trace ("\n adjusted " ++ show adjusted) True
  = adjusted : new_function : tl
  where -- the case construct being replaced
        xcase = detsubexpr expr path
        -- the variable to be passed to the new function (preliminary)
        (_, var_list) = get_var_list xcase
        -- the name of the new functiomn
        new_name = get_new_name qname counter
        -- the arguments of the function being called
        new_args = map Var var_list
        -- the function that executes the replaced case
        new_function = get_new_function new_name var_list xcase
        -- the call that replaces the case construct
        new_expr = replace expr path (Comb FuncCall new_name new_args)
        -- the adjusted function that was holding the case being replaced
        adjusted = Func qname arity visibility typeexpr (Rule varindexlist new_expr)


transform_nonvar path counter
    (Func qname arity visibility typeexpr a@(Rule varindexlist expr) : tl)
  -- | trace ("\n xcase " ++ show xcase) True    
  --   && trace ("\n prelim_var_list " ++ show prelim_var_list) True    
  --   && trace ("\n new_var " ++ show new_var) True    
  --   && trace ("\n var_list " ++ show var_list) True
  --   && trace ("\n new_args " ++ show new_args) True
  --   && trace ("\n new_name " ++ show new_name) True
  --   && trace ("\n new_function " ++ show new_function) True
  --   && trace ("\n new_expr " ++ show new_expr) True
  --   && trace ("\n adjusted " ++ show adjusted) True
  = adjusted : new_function : tl
  where -- the case construct being replaced
        xcase@(Case flex select branches) = detsubexpr expr path
        -- the variable to be passed to the new function and a new variable
        (new_var, prelim_var_list) = get_var_list xcase
        -- the list of indexes of variables of the new function
        var_list = new_var : prelim_var_list
        -- the arguments of the function being called
        new_args = select : map Var prelim_var_list
        -- the name of the new functiomn
        new_name = get_new_name qname counter
        -- the function that executes the replaced case
        new_function = get_new_function new_name var_list
             (Case flex (Var new_var) branches)
        -- the call that replaces the case construct
        new_expr = replace expr path (Comb FuncCall new_name new_args)
        -- the adjusted function that was holding the case being replaced
        adjusted = Func qname arity visibility typeexpr (Rule varindexlist new_expr)

------------------------------------------------------------------

-- Compute the variables of the new function and a new fresh variable
-- These are the variable occurring in the case less the 
-- the variable introduced by withint the case (patterns and lets)
get_var_list :: Expr -> (Int,[Int])
get_var_list xcase
  -- | trace ("\nget_var_list " ++ show (prelim,local,newvar)) True
  = (newvar, prelim \\ local)
  where prelim = nub (all_vars xcase)
        newvar = if prelim == [] then 1 else (maximum prelim + 1)
        local  = nub (case_vars xcase)

-- the name of the function that replaces the case expression
get_new_name :: QName -> Int -> QName
get_new_name (mod,unqual) count = (mod,unqual++"_case_#"++show count)

-- The body of the function that replaces the case expression
-- The type is bogus, the rule is unchanged
get_new_function :: QName -> [Int] -> Expr -> FuncDecl
get_new_function qname var_list xcase
  = Func qname (length var_list) Private (TVar 0) (Rule var_list xcase)

-- these are all the variables occurring in an expression
all_vars :: Expr -> [Int]
all_vars (Var i) = [i]
all_vars (Lit _) = []
all_vars (Comb _ _ expr_list) = concat (map all_vars expr_list)
all_vars (Let index_expr_list expr)
  = concat (map all_vars (map snd index_expr_list)) ++ all_vars expr
all_vars (Free var_list expr) = var_list ++ all_vars expr
all_vars (Or expr1 expr2) =  all_vars expr1 ++ all_vars expr2
all_vars (Case _ expr branch_list)
  = all_vars expr
      ++ concat [all_vars n_expr | Branch _ n_expr <- branch_list]
all_vars (Typed expr _) = all_vars expr

-- these are all the variables declared within the case expression
-- been replaced, hence they are not passed in.
case_vars :: Expr -> [Int]
case_vars (Var _) = []
case_vars (Lit _) = []
case_vars (Comb _ _ expr_list) = concat (map case_vars expr_list)
case_vars (Let index_expr_list expr)
  = map fst index_expr_list
       ++ concatMap case_vars (map snd index_expr_list)
           ++ case_vars expr
case_vars (Free var_list expr) = var_list ++ case_vars expr
case_vars (Or expr1 expr2) =  case_vars expr1 ++ case_vars expr2
case_vars (Case _ expr branch_list)
  = case_vars expr
      ++ concat [case_vars n_expr ++ pcase_var patt_list
                   | Branch patt_list n_expr <- branch_list]
  where pcase_var (LPattern _) = []
        pcase_var (Pattern _ var_list) = var_list
case_vars (Typed expr _) = case_vars expr

{-  
From FlatCurry.Types

data Expr
  = Var VarIndex
  | Lit Literal
  | Comb CombType QName [Expr]
  | Let [(VarIndex, Expr)] Expr
  | Free [VarIndex] Expr
  | Or Expr Expr
  | Case CaseType Expr [BranchExpr]
  | Typed Expr TypeExpr
-}

-- Arguments are: expression -> path
-- The result is the subexpression at path
subexpr :: Expr -> [Int] -> Expr
subexpr expr [] = expr
subexpr (Comb _ _ (y++[x]++_)) (p:ps)
  | p =:= length y
  = subexpr x ps
subexpr (Let (y++[(_, x)]++_) _) (p:ps)
  | p =:= length y
  = subexpr x ps
subexpr (Let _ x) (-1:ps)
  = subexpr x ps
subexpr (Free _ x) (-1:ps)
  = subexpr x ps
subexpr (Or x _) (1:ps)
  = subexpr x ps
subexpr (Or _ x) (2:ps)
  = subexpr x ps
subexpr (Case _ x _) (-1:ps)
  = subexpr x ps
subexpr (Case _ _ (y++[Branch _ x]++_)) (p:ps)
  | p =:= length y
  = subexpr x ps
subexpr (Typed x _) (-1:ps)
  = subexpr x ps

-- Arguments are: expression_1 -> path -> expression_2
-- The result is expression_1 with the subexpression at path replaced by expression_2
-- TODO: use a case instead of pattern matching to eliminate non-determinism
replace :: Expr -> [Int] -> Expr -> Expr
replace _ [] rep = rep
replace (Comb combtype qname args) (p:ps) rep
  = Comb combtype qname (y++[replace x ps rep]++z)
  where (y,x:z) = splitAt p args
replace (Let binds expr) (p:ps) rep
  | p == -1 = Let binds (replace expr ps rep)
  | p >= 0  = Let (y++[(i, replace x ps rep)]++z) expr
  where (y,(i,x):z) = splitAt p binds
replace (Free var_list x) (-1:ps) rep
  = Free var_list (replace x ps rep)
replace (Or x y) (p:ps) rep
  | p == 1 = Or (replace x ps rep) y
  | p == 2 = Or x (replace y ps rep)
replace (Case casetype expr branch_list) (p:ps) rep
  | p == -1 = Case casetype (replace expr ps rep) branch_list
  | p >= 0  = Case casetype expr (y++[Branch pattern (replace x ps rep)]++z)
  where (y,(Branch pattern x):z) = splitAt p branch_list
replace (Typed x xtype) (-1:ps) rep
  = Typed (replace x ps rep) xtype

-- Compute in expr the path of a case expression
-- whose selector is not a variable
find_case_nonvar_select :: Expr -> DET (Maybe [Int])
find_case_nonvar_select expr
  | subexpr expr p == x &&
    nonvar x
  = Just p
  where p free
        x = Case _ _ _
        nonvar (Case _ select _)
          = case select of
              Var _ -> False
              _     -> True
find_case_nonvar_select'default _ = Nothing

-- Find just one solution of find_under, if it exists, and forget the rest
find_under_wrapper :: Bool -> Expr -> [Int] -> DET (Maybe [Int])
find_under_wrapper b e il
  -- | trace ("\nfind_under_wrapper normal in " ++ (show (b,e,il))) True
  --   && trace ("\nfind_under_wrapper normal out " ++ (show result)) True
  | result =:= result
  = Just result
  where result = reverse (find_under b e il)
find_under_wrapper'default _ _ _ = Nothing

-- Compute in expr the path of a case expression
-- occuring as a subexpression of some construct.
-- These cases must be replaced by function calls.
find_under :: Bool -> Expr -> [Int] -> [Int]
find_under _ (Comb _ _ (y++[x]++_)) ps = find_under True x (length y:ps)
find_under _ (Let (y++[(_, x)]++_) _) ps = find_under True x (length y:ps)
find_under _ (Let _ x) ps = find_under True x (-1:ps)
find_under b (Free _ x) ps = find_under b x (-1:ps)
find_under _ (Or x _) ps = find_under True x (1:ps)
find_under _ (Or _ x) ps = find_under True x (2:ps)
find_under True (Case _ _ _) ps = ps
find_under False (Case _ x _) ps = find_under True x (-1:ps)
find_under False (Case _ _ (y++[Branch _ x]++_)) ps = find_under True x (length y:ps)
find_under b (Typed x _) ps = find_under b x (-1:ps)

-- Arguments are: expression -> path
-- The result is the subexpression at path
detsubexpr :: Expr -> [Int] -> Expr
detsubexpr expr [] = expr
detsubexpr (Comb _ _ x) (p:ps) = detsubexpr (x !! p) ps
detsubexpr (Let x y) (p:ps)
  | p == -1 = detsubexpr y ps
  | p >= 0   = detsubexpr (snd (x !! p)) ps
detsubexpr (Free _ x) (-1:ps) = detsubexpr x ps
detsubexpr (Or x y) (p:ps)
  | p == 1 = detsubexpr x ps
  | p == 2 = detsubexpr y ps
detsubexpr (Case _ y x) (p:ps)
  | p == -1 = detsubexpr y ps
  | p >= 0   = let Branch _ e = x !! p in detsubexpr e ps
detsubexpr (Typed x _) (-1:ps) = detsubexpr x ps

