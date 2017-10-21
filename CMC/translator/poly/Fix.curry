import ICurry

------------------------------------------------------------------
-- This works because the variables occur only in Return statements
-- and each variable occurs only once.
-- Traverse the body of an equality function and instantiate the identifier
-- of each ICurry variable, which is a free Curry variable, to a distinguished integer

fixBody c [] = c
fixBody c (s:ss) = fixBody (fixStmt c s) ss
fixStmt c stmt =
   case stmt of
     Declare (Variable x _) -> x =:= c &> c+1   -- !!!
     ATable _ _ _ ce_list -> foldl fixStmt c (concatMap snd ce_list)
     _ -> c

{-
------------------------------------------------------------------
-- This works because the variables occur only in Return statements
-- and each variable occurs only once.
-- Traverse the body of an equality function and collectevery ICurry variable.

collectBody :: [Variable] -> [Statement] -> [Variable] 
collectBody table [] = table
collectBody table (s:ss) = collectBody (collectStmt table s) ss
collectStmt table stmt =
   case stmt of
     Return expr -> collectExpr table expr
     ATable _ _ _ ce_list -> foldl collectStmt table (concatMap snd ce_list)
     BTable _ _ _ ce_list -> foldl collectStmt table (concatMap snd ce_list)
     _ -> table

collectExpr table Exempt = table
collectExpr table (Reference v) = v : table      -- !!!!!!!!!
collectExpr table (BuiltinVariant _) = table
collectExpr table (Applic _ _ e_list) = foldl collectExpr table e_list
collectExpr table (PartApplic _ expr) = collectExpr table expr
collectExpr table (IOr expr1 expr2) = collectExpr (collectExpr table expr1) expr2

-}
