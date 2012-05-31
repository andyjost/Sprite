module ShowLOIS(
                showProgram,
                showQName,
                showConstructorDecl,
                showOperationDecl,
                showDefinitionalTree,
                showRulePattern,
                showLiteral,
                showExpr
               ) where

import LOIS
import Util

{-
Functions to pretty print LOIS data as a string. The functions are called show[type] where type is the name of a LOIS type.
-}


showQName (m, n) = m ++ "." ++ n

showProgram (Program types ops) = mkString "\n" types' ++ "\n\n\n" ++ mkString "\n" ops'
              where types' = map showTypeDecl types
                    ops' = map showOperationDecl ops

showTypeDecl (TypeDecl name cons) = "data " ++ showQName name ++ " =\n" ++ mkString "\n" cons'
	      where cons' = map showConstructorDecl cons

showConstructorDecl (ConstructorDecl name arity) = 
                "    " ++ (showQName name) ++ " :: " ++ (show arity)

showOperationDecl (OperationDecl name arity deftree) =
                (showQName name) ++ " :: " ++ (show arity) ++ "\n" ++
                showDefinitionalTree 0 deftree

ind i = replicate (i*2) ' '

showDefinitionalTree i (Branch pat v complete subtrees) = 
                (ind i) ++ (showRulePattern pat) ++ " -> case " ++ (showVariable v) ++ " of\n" ++
                (concatMap (showDefinitionalTree (i+1)) subtrees) ++
                if not complete then (ind (i+1)) ++ "default -> failure\n" else ""
showDefinitionalTree i (Rule pat expr) = 
                (ind i) ++ (showRulePattern pat) ++ " -> " ++ showExpr expr ++ "\n"
showDefinitionalTree i (Exempt pat) = 
                (ind i) ++ (showRulePattern pat) ++ " -> failure\n"
showDefinitionalTree i (BuiltIn n) = 
                (ind i) ++ "external " ++ n ++ "\n"

showRulePattern (NodePattern (symbol n) vars) = 
               if not $ null vars then
                 "(" ++ (showQName n) ++ " " ++ (mkString " " (map showVariable vars)) ++ ")"
               else
                 (showQName n)
showRulePattern (LitPattern lit) = 
                "(" ++ showLiteral lit ++ ")"

showLiteral = show

varLetters = "abcdxyzijkmnqrstuvw"

showVariable i = if i > 0 && i <= length varLetters then [varLetters !! (i-1)]
                 else "v" ++ show i

showExpr (Variable v) = showVariable v
showExpr (Node (symbol n) args) = 
               if not $ null args then
                 "(" ++ (showQName n) ++ " " ++ (mkString " " (map showExpr args)) ++ ")"
               else
                 (showQName n)
showExpr (Partial (symbol n) args) = 
               if not $ null args then
                 "[" ++ (showQName n) ++ " " ++ (mkString " " (map showExpr args)) ++ "]"
               else
                 "[" ++ (showQName n) ++ "]"
showExpr (Choice a b) =
                (showExpr a) ++ " ? " ++ (showExpr b)
showExpr (LitNode lit) = 
                "(" ++ showLiteral lit ++ ")"
showExpr (Generator) = "Generator"
