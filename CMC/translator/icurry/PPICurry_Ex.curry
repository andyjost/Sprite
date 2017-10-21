module PPICurry_Ex where

import ICurry

execute (IModule name imported_list data_list funct_list)
  = "\n" ++ "module " ++ show name ++
       ppImported imported_list ++
       foldr ((++) . ppData) "" data_list ++
       foldr ((++) . ppFunction) "" funct_list

ppImported imported_list
  = "\n  import" ++
       foldr ((++) . ("\n    " ++ )) ""
           (map (\x -> "\"" ++ x ++ "\"") imported_list) -- quote

ppData (qname, constr_list)
  = "\n  data " ++ ppIName qname ++
      foldr ((++) . ppConstructor) "" (zip constr_list [0..])

ppConstructor (IConstructor qname arity, index)
  = "\n    constructor " ++ ppIName qname ++ " " ++ show arity ++ " " ++ show index

ppFunction (IFunction qname arity stmt_list)
  = "\n  function " ++ ppIName qname ++ " " ++ show arity ++
       "\n    code" ++ 
       foldr ((++) . ppStmt 6) "" stmt_list

------------------------------------------------------------------

ppVariable n string (Variable i x)
 = ppIndent n ++ string ++ show i ++ " " ++ show x

------------------------------------------------------------------

ppStmt n (IExternal string)
  = ppIndent n ++ "external \"" ++ string ++ "\""

ppStmt n (Comment string)
  = ppIndent n ++ "comment \"" ++ string ++ "\""

ppStmt n (Return expr)
  = ppIndent n ++ "return" ++ ppExpr (n+2) expr

ppStmt n (Declare (Variable i x))
  = ppIndent n ++ "declare_var " ++ show i ++ " " ++ show x

ppStmt n (Assign i expr)
  = ppIndent n ++ "assign " ++ show i ++
      ppExpr (n+2) expr

ppStmt n (Fill i path j)
  = ppIndent n ++ "fill " ++ show i ++ " with " ++ show j ++
       ppIndent (n+2) ++ "at" ++
       foldr ((++) . (\ (s,k) -> " " ++ ppIName s ++ ":" ++ show k)) "" path

ppStmt n (ATable suffix flex expr branch_list)
  = ppIndent n ++ 
      "ATable " ++ show suffix ++ " " ++ show (length branch_list) ++ " " ++ flex_show flex ++
      ppExpr (n+2) expr ++
      foldr ((++) . ppABranch (n+2)) "" branch_list

ppStmt n (BTable suffix flex expr branch_list)
  = ppIndent n ++ 
      "BTable " ++ show suffix ++ " " ++ show (length branch_list) ++ " " ++ flex_show flex ++
      ppExpr (n+2) expr ++
      foldr ((++) . ppBBranch (n+2)) "" branch_list

ppShowVariableRef ((index,_,_):_)
  = show index

ppABranch n (IConstructor qname {-arity-}_, stmt_list)
  = ppIndent n ++ ppIName qname ++ " =>" ++
      foldr ((++) . ppStmt (n+2)) "" stmt_list

ppBBranch n (lit, stmt_list)
  = ppIndent n ++ lit_show lit ++ " =>" ++
      foldr ((++) . ppStmt (n+2)) "" stmt_list

flex_show False = "rigid"
flex_show True = "flex"

lit_show (Bint i) = "int " ++ show i
lit_show (Bchar c) = "char " ++ show c
lit_show (Bfloat x) = "float " ++ show x

------------------------------------------------------------------

ppExpr n Exempt
  = ppIndent n ++ "exempt"

ppExpr n (Reference i)
  = ppIndent n ++ "reference_var " ++ (show i)

ppExpr n (BuiltinVariant (Bint i))
  = ppIndent n ++ "int " ++ show i

ppExpr n (BuiltinVariant (Bchar i))
  = ppIndent n ++ "char " ++ show i

ppExpr n (BuiltinVariant (Bfloat i))
  = ppIndent n ++ "float " ++ show i

ppExpr n (Applic _ qname expr_list)
  = ppIndent n ++
       "Node " ++ ppIName qname ++
       ppArgList (n+2) expr_list

ppExpr n (PartApplic missing expr)
  = ppIndent n ++
       "partial " ++ show missing ++ " (" ++
       ppExpr (n+2) expr ++
       " )"

-- TODO: this should be removed
ppExpr n (IOr expr_l expr_r)
  = ppIndent n ++ "Or (" ++ 
       ppExpr (n+2) expr_l ++ " ," ++ ppExpr (n+2) expr_r ++
       " )"

------------------------------------------------------------------

ppArgList _ [] = ""

ppArgList n [x]
  = " (" ++ ppExpr n x ++ " )"

ppArgList n (x1:x2:xs)
  = " (" ++
       ppExpr n x1 ++
       foldr ((++) . aux) "" (x2:xs) ++
       " )"
    where aux x = " ," ++ ppExpr n x

------------------------------------------------------------------

ppIName (s,n) = "\"" ++ s ++ "." ++ n ++ "\""

ppIndent indent
  = "\n" ++ take indent (repeat ' ')
