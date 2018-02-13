{-# OPTIONS_CYMAKE -Wnone #-} -- no warnings

-- This program makes big assumptions on Flatcurry.  These assumption
-- should be guaranteed by Norm.  In a FlatCurry expression,
-- multibranch tables and let blocks are outermost.  They can be
-- nested.
--
-- An expression is found is several contexts (see ICurry syntax).
-- In particular, the bindings of a let block and the selector of
-- a multibranch table are expressions.

module FlatToICurry(execute) where

import FlatCurry.Types
import ICurry
import LetPlan

-- ttable is used to complete and reorder the branches of an ATable.

execute :: [(a,[(QName,Int)])] -> Prog -> IModule
execute type_table (Prog name imported type_list funct_list _)
  = IModule name imported constr_decl funct_decl
  where constr_decl = [makeType x | x@(Type _ _ _ _) <- type_list]
        funct_decl = map (makeFunct type_table) funct_list

makeType :: TypeDecl -> (IName, [IConstructor])
makeType (Type qname _ _ constr_list)
  = (qname, [IConstructor cname arity | (Cons cname arity _ _) <- constr_list])

makeFunct :: [(a,[(QName,Int)])] -> FuncDecl -> IFunction
makeFunct type_table (Func qname arity _ _ rule)
  = IFunction qname arity (makeRule qname type_table rule)

makeRule :: QName -> [(a,[(QName,Int)])] -> Rule -> [Statement]
makeRule _ _ (External x) = [IExternal x]
makeRule qname ttable (Rule var_list expr) 
  = [Declare (Variable n (ILhs (qname,k))) | (k,n) <- zip [1..] var_list]
      -- TODO: is a free variable in the rule variable list ???
      -- I do not think so !!!
      ++ makeStmt ttable expr

-- Some statements are simply an expression to be returned, see last entry
-- Others have case or local declarations that precede the return statement.
makeStmt :: [(a,[(QName,Int)])] -> Expr -> [Statement]
makeStmt ttable stmt =
  case stmt of
    Free var_list expr
       -> makeFree var_list ++ makeStmt ttable expr
    Case _ expr (Branch (Pattern _ _) _ : _)
       -> makeCaseAPattern ttable stmt ++ makeStmt ttable expr
    Case _ expr (Branch (LPattern _) _ : _)
       -> makeCaseBPattern ttable stmt ++ makeStmt ttable expr
    Typed expr _
       -> makeStmt ttable expr
    Let _ expr
       -> makeLet ttable stmt 
    plain
       -> [Return (makeExpr ttable plain)]

------------------------------------------------------------------

makeFree :: [Int] -> [Statement]
makeFree var_list = [Declare (Variable i IFree) | i <- var_list]

-- The selector of the case is guaranteed to be a variable
makeCaseAPattern :: [(a,[(QName,Int)])] -> Expr -> [Statement]
makeCaseAPattern ttable (Case flex (Var i) branch_list@(Branch (Pattern cname _) _ : _))
  = [ATable counter (flex==Flex) (Reference i) new_branch_list]
  where counter = unknown    -- later replace with an int 
        -- get the complete list of constructors labeling the table
        constr_list = get_constr_list cname ttable
        get_constr_list dname (_ ++ [(_, a@(_ ++ [(dname,_)] ++ _))] ++ _) = a
        new_branch_list = map choose_create constr_list
        choose_create (dname, arity)
          = case blookup dname branch_list of
              Nothing -> (IConstructor dname arity, [Return Exempt])
              Just (Branch (Pattern _ var_list) branch_expr) 
                  -> (IConstructor dname arity, 
                         [Declare (Variable n (IVar i (dname,k)))
                                   | (k,n) <- zip [1..] var_list]
                            ++ makeStmt ttable branch_expr)
        blookup _ [] = Nothing
        blookup dname (a@(Branch (Pattern pname _) _) : z)
          | dname == pname = Just a
          | otherwise = blookup dname z


-- The selector of the case is guaranteed to be a variable
makeCaseBPattern :: [(a,[(QName,Int)])] -> Expr -> [Statement]
makeCaseBPattern ttable (Case flex (Var i) branch_list@(Branch (LPattern _) _ : _))
  = [BTable counter (flex==Flex) (Reference i)
          [(translate pattern, makeStmt ttable branch_expr) 
              | (Branch (LPattern pattern) branch_expr) <- branch_list]]
  where counter = unknown  -- later replace with an int
        translate (Intc x) = Bint x
        translate (Charc x) = Bchar x
        translate (Floatc x) = Bfloat x

makeLet :: [(a,[(QName,Int)])] -> Expr -> [Statement]
makeLet ttable (Let bind_list expr)
  = Comment (show (sorted_list)) :
       execute_plan ttable bind_list plan
          ++ makeStmt ttable expr
  where (sorted_list, plan) = make_plan bind_list

------------------------------------------------------------------

makeExpr :: a -> Expr -> Expression
makeExpr _ (Var i) = Reference i
makeExpr _ (Lit (Intc x)) = BuiltinVariant (Bint x)
makeExpr _ (Lit (Charc x)) = BuiltinVariant (Bchar x)
makeExpr _ (Lit (Floatc x)) = BuiltinVariant (Bfloat x)

makeExpr ttable (Comb FuncCall qname expr_list)
  = Applic False qname (map (makeExpr ttable) expr_list)
makeExpr ttable (Comb ConsCall qname expr_list)
  = Applic True qname (map (makeExpr ttable) expr_list)
makeExpr ttable (Comb (FuncPartCall missing) qname expr_list)
  = PartApplic missing (Applic False qname (map (makeExpr ttable) expr_list))
makeExpr ttable (Comb (ConsPartCall missing) qname expr_list)
  = PartApplic missing (Applic True qname (map (makeExpr ttable) expr_list))
makeExpr ttable (Or expr_1 expr_2) = IOr (makeExpr ttable expr_1) (makeExpr ttable expr_2)
makeExpr ttable (Typed expr _) = makeExpr ttable expr

makeExpr _ (Free _ _) =  error "FlatToICurry found a free variable while making an expression"
makeExpr _ (Case _ _ _) = error "FlatToICurry found a multibranch case while making an expression"
makeExpr _ (Let _ _) = error "FlatToICurry found a let-block while making an expression"

-- makeStmt ttable x = [Comment ("do " ++ show x ++ "  " ++ show ttable)]

execute_plan :: a -> [(Int, Expr)] -> [Action] -> [Statement]
execute_plan ttable bind_list plan
  = concatMap (execute_plan_step ttable bind_list) plan

execute_plan_step :: a -> [(Int, Expr)] -> Action ->DET [Statement]
execute_plan_step _ _ (Pforward i) = [Declare (Variable i IBind)]
execute_plan_step ttable (_ ++ [(i, expr)] ++ _) (Passign i)
  = [Assign i (makeExpr ttable expr)]
execute_plan_step ttable (_ ++ [(i, expr)] ++ _) (Pinitialize i)
  = [Declare (Variable i IBind),
     Assign i (makeExpr ttable expr)]
execute_plan_step _ (_ ++ [(i, expr)] ++ _) (Pfill i j)
  = [Fill i (reverse p) j | p <- find_path_set expr j]
