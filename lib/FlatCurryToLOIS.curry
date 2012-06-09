module FlatCurryToLOIS(main, process, load, requiredSymbols) where

import LOIS
import qualified ShowLOIS

import FlatCurry hiding (QName, TypeDecl)
import CompactFlatCurry
import qualified FlatCurry as FC
import IO
import System 
import List
import Maybe(fromJust,mapMaybe)
import Unsafe(trace)

import Util

import FlatCurryShow 

requiredSymbols = [alwaysRequired ("Prelude","?")] ++ defaultRequired

main name = do
     _ <- system ("parsecurry -"++"-flat " ++ name)
     -- curryProg <- computeCompactFlatCurry [Main "main", Required requiredSymbols] name
     curryProg <- readFlatCurry name
     putStrLn (showFlatProg curryProg)
     let r = process curryProg
     putStrLn (ShowLOIS.showProgram r)

load name = do
     _ <- system ("parsecurry -"++"-flat " ++ name)
     curryProg <- computeCompactFlatCurry [Main "main", Required requiredSymbols] name
     --putStrLn (showFlatProg curryProg)
     return $ process curryProg

-- Transformation state

data State = State Prog (Maybe (Either FC.TypeDecl FC.FuncDecl)) [Int] [VarIndex]
-- The program
-- The declaration we are working with (or None if we are at the whole program level)
-- The "path" to the current position (this is needed to generate unique new function symbols for sub expressions)
-- The list of variables currently in scope

-- Build a State with default values (except for prog)
newState prog = State prog Nothing [] []

-- Accessors
getProg (State p _ _ _) = p
getProgName (State (Prog n _ _ _ _) _ _ _) = n
getFuncDecl (State _ v _ _) = case v of
                              Just (Right f) -> Just f
                              _ -> Nothing
getDeclName (State _ v _ _) = case v of
                              Just (Right (Func n _ _ _ _)) -> n
                              Just (Left (Type n _ _ _)) -> n
                              Just (Left (TypeSyn n _ _ _)) -> n
                              _ -> ("__none__","__none__")
getPath (State _ _ p _) = p
setPath p (State prog decl _ vars) = State prog decl p vars

-- Add a number to the path
addToPath n (State prog decl path vars) = State prog decl (n : path) vars
-- Add a variable to the list of used variables 
addVar n (State prog decl path vars) = State prog decl path (n : vars)
-- Add multiple variable to the list of used variables.
addVars ns st = foldl (\s n-> addVar n s) st ns
-- Set the current declaration.
setDecl d (State prog _ path vars) = State prog d path vars

-- Create an identifier based on the current decl and the current path.
makeName st@(State _ _ path _) = (mod, name ++ "__" ++ (mkString "_" (map show path)))
         where (mod, name) = getDeclName st
-- Get the next variable ID that has not been used as listed in the state or anywhere in the given expr.
nextVar (State _ _ _ vars) expr = (foldr max 1 (vars ++ referencedVars expr)) + 1
 
-- Find a type given the qname of one of its constructors.
getTypeByConstr (Prog _ _ types _ _) name =
        find isType types
    where isType t = case t of
             (Type _ _ _ cons) -> hasThisCons cons
             _ -> False
          hasThisCons l = any (\(Cons n _ _ _)-> n == name) l 

-- Actual FlatCurry processing
process p@(Prog pname imports types funcs _) = Program imports (concatMap procType types) 
                    (removeDuplicateFuncs $ concatMap (procFunc (newState p)) funcs)

removeDuplicateFuncs l = nubBy sameName l
                where sameName (OperationDecl a _ _) (OperationDecl b _ _) = a == b

-- Handle types
procCons (Cons cname arity _ _) = ConstructorDecl cname arity
procType (Type tname vis args cons) = [TypeDecl tname (map procCons cons)]
procType (TypeSyn tname vis args tyexpr) = [] -- Types to not exist in the runtime so type synanyms are meaningless.

-- Handle functions

-- Take a function and generate a list of operations that implement it in LOIS.
procFunc st d@(Func fname arity vis ty rule) = OperationDecl fname arity deftree : otherops
    where (deftree, otherops) = procRule st' fname rule
          st' = setPath [] $ setDecl (Just $ Right d) st 

procRule st fname (FC.Rule args expr) = procExpr st' (NodePattern (OperationSym fname) args) expr
     where st' = addVars args (addToPath 0 st)
procRule st fname (FC.External name) = (BuiltIn name, [])

-- Check if an FC.Expr is a Simple RHS. That is, it is only made up of variable references, literals, choices and function/constructor applications.
isExprSimpleRHS :: FC.Expr -> Bool
isExprSimpleRHS x = case x of
                      Lit _ -> True
                      Var _ -> True
                      Comb _ _ args -> all isExprSimpleRHS args
                      Or a b -> isExprSimpleRHS a && isExprSimpleRHS b 
                      _ -> False

-- Build a list of exempt nodes for all the constructors that are NOT mentioned in the set of branches
makeExempts cons constrs = exempts 
        where exempts = concatMap toExempt cons
              toExempt (Cons cname arity _ _) = 
                    if cname `elem` constrs then []
                    else
                      [Exempt (NodePattern (ConstructorSym cname) [1001..1000+arity])]


-- Convert an expression to a definitional tree and a list of other generated accilery functions.
procExpr :: State -> RulePattern -> FC.Expr -> (DefinitionalTree, [OperationDecl])
procExpr st pat expr =
     if isExprSimpleRHS expr then 
           -- If the expr is a Simple RHS just generate a rule node with the appropriate definitional tree
           (LOIS.Rule pat (procSimpleRHS expr), [])
     else case expr of
        (Case _ (Var v) branches) -> 
           -- If we have a case where the scutinee is a variable then we generate a Branch node with the appropiate subtrees.
           let (subtrees, operationLists) = unzip $ mapWithIndex (\i b -> procBranch (addToPath i st) b) branches 
               constrs = mapMaybe getConstrFromBranch branches
               -- Find the type of the scutinee based on the constructor that we have
               exempts = if not $ null constrs then
                            case getTypeByConstr (getProg st) (head constrs) of
                              Nothing -> [] -- It must be a built-in so there are no exempts
                              Just (Type _ _ _ cons) -> makeExempts cons constrs
                         else
                            []
               isComplete = not $ null constrs
                 in
           (LOIS.Branch pat v isComplete (subtrees ++ exempts), concat operationLists) 
        (Let lets body) -> 
           -- To handle "let" we generate a new function for the body of the let and pass it every value is 
           -- needs as arguments including all the values bound by the let.
           let 
               letVars = map fst lets
	       -- check if the given binding is dependant on other bindings.
               isDependant (_, e) = any (`elem` letVars) $ referencedVars e 
	       -- partition the binding into the dependant ones and the non dependant ones
               (depLets, nonDepLets) = partition isDependant lets 
	       -- Build a new Let for dependant bindings if there are any.
               body' =  if null depLets then body else (Let depLets body) 
	       -- get a list of all the non-dep variables referenced in the body so we can pass them all to it.
               vars = referencedVars body' 
	       -- build a list of arguments to pass. This is a mix of simple Vars and complex expressions.
               args = map findVal vars 
               findVal vn = case lookup vn nonDepLets of
                        Just e -> e
                        Nothing -> (Var vn)
               name = makeName st
               rule = (FC.Rule vars body')
               -- Generate a definitional tree to make a call to the generated function
               (dt, oops) = procExpr (addToPath 0 st) pat (Comb FuncCall name args)
               -- Generated the accilary function itself.
               mops = procFunc st (Func name (length vars) Private (TVar (-1)) rule)
                 in
           --trace (showThings [("lets, body",show (lets,body)),("vars",show vars),("depLets",show depLets),("nonDepLets",show nonDepLets)]) $
           if null nonDepLets && not (null depLets) then
             error ("Recursive let detected in " ++ show (getDeclName st) ++ ": " ++ show expr)
           else 
             (dt, oops ++ mops)
        (Free frees body) -> 
           let vars = referencedVars body -- get a list of all the variables referenced in the body so we can pass them all to it.
               args = map findVal vars -- build a list of arguments to pass. This is a mix of simple Vars and generators.
               findVal vn = case vn `elem` frees of
                        True -> Generator
                        False -> (Variable vn)
               name = makeName st
               rule = (FC.Rule vars body)
               -- Generate a definitional tree to make a call to the generated function
               dt = LOIS.Rule pat (Node (OperationSym name) args)
               -- Generated the accilary function itself.
               mops = procFunc st (Func name (length vars) Private (TVar (-1)) rule)
                 in
           (dt, mops)
        (Or a b) -> 
           procExpr st pat (Comb FuncCall ("Prelude", "?") [a, b])
        --Case with non-Var scrutinee
        (Case ty scrut branches) -> 
           -- For Cases whose scrutinees are not Vars we generate a let clause that binds scrutinee 
           -- to a local and then to the case with the bound locals. The Let handling code will 
           -- generate a new function.
           let vars = scrutVar : referencedVars expr -- get a list of all the variables referenced in the body so we can pass them all to it.
               scrutVar = nextVar st expr
               st' = addVar scrutVar st
               lets = [(scrutVar, scrut)]
                 in
           procExpr (addToPath 0 st') pat (Let lets (Case ty (Var scrutVar) branches))
        (Comb ty name args) -> 
           -- For function calls whose args are not simple, we lift each non-simple argument into 
           -- it's own function and then output calls to those functions.
           let (args', oops, st') = foldl cleanArg ([], [], st) args
               cleanArg (args, oops, st) e = 
                          if isExprSimpleRHS e then (e:args, oops, st) 
                          else let (e', ops) = liftExpr st e in 
			       (e' : args, ops ++ oops, (addToPath 1 st)) 
               (dt, mops) = --trace (showThings [("expr",show expr),("args",show args),("args'",show args')]) 
                    procExpr (addToPath 0 st') pat (Comb ty name args')
                 in
             --trace (showThings [("expr",show expr),("args'",show args')])  
               (dt, oops ++ mops)
        e -> error ("Unsupported expression: " ++ (show e))

liftExpr :: State -> FC.Expr -> (FC.Expr, [OperationDecl])
liftExpr st expr = 
   let vars = referencedVars expr -- get a list of all the variables referenced in the body so we can pass them all to it.
       args = map Var vars -- build a list of arguments to pass. This is a mix of simple Vars and complex expressions.
       name = makeName st
       rule = (FC.Rule vars expr)
       -- Generate a call to the generated function
       retExpr = (Comb FuncCall name args)
       -- Generated the accilary function itself.
       mops = procFunc st (Func name (length vars) Private (TVar (-1)) rule)
         in
       (retExpr, mops)

showThings ((s, x) : xs) = s ++ ": " ++ x ++ "\n" ++ showThings xs
showThings [] = ""

-- Recursively walk an expression and build a list of all the referenced variables.
referencedVars :: FC.Expr -> [VarIndex]
referencedVars expr = nub $ h expr
    where h expr = case expr of
                (Var x) -> [x] 
                (Let lets body) -> deleteAll (map fst lets) $ nub (concatMap referencedVars (body : map snd lets))
                (Free vars body) -> deleteAll vars $ referencedVars body  
                (Comb _ _ args) -> nub $ concatMap referencedVars args  
                (Or a b) -> nub $ concatMap referencedVars [a, b]  
                (Case _ sc branchs) -> 
                      --let bound = (\ (FC.Branch p _) -> p) branchs) 
                      let refedByBranch (FC.Branch pat expr) = 
                                deleteAll (boundVars pat) $ referencedVars expr in
                      nub $ concat (referencedVars sc : map refedByBranch branchs)   
                _ -> []

-- Get the list of variables bound by a pattern
boundVars :: FC.Pattern -> [VarIndex]
boundVars (LPattern _) = []
boundVars (Pattern _ vs) = vs

deleteAll r l = filter (`notElem` r) l 

-- Extract the constructor name from a FC.Branch
getConstrFromBranch b = case b of
        (FC.Branch (Pattern qname _) _) -> Just qname
        _ -> Nothing

-- Build a definitional tree (and a list of other functions) from a branch
procBranch st (FC.Branch pat expr) = procExpr st (procPattern st pat) expr
-- Build a LOIS.RulePattern from an FC.Pattern
procPattern st (Pattern qname vars) = NodePattern (ConstructorSym qname) vars
procPattern st (LPattern lit) = LitPattern (procLit lit)

-- Build a LOIS.Literal from a FC.Literal
procLit lit = case lit of 
                (Intc x) -> LInt x
                (Floatc x) -> LFloat x
                (Charc x) -> LChar x

-- Build a LOIS.Expr from an FC.Expr that is a Simple RHS. This is done by almost direct mapping.
procSimpleRHS (Lit l) = LitNode (procLit l)
procSimpleRHS (Var n) = Variable n
procSimpleRHS (Comb ty name args) = nodeTy (symTy name) (map procSimpleRHS args)
   where 
  -- Map a FC Comb type to an LOIS.Symbol constructor. This can be called like: symty ctype qname
     symty FuncCall = (OperationSym, Node)
     symty ConsCall = (ConstructorSym, Node)
     symty (FuncPartCall n) = (OperationSym, Partial)
     symty (ConsPartCall n) = (ConstructorSym, Partial)
     (symTy, nodeTy) = symty ty
procSimpleRHS (Or a b) = Choice (procSimpleRHS a) (procSimpleRHS b)




debug s x = x -- trace ((show s) ++ "\n") x
