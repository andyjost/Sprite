-- An expression parser from functional patterns.
--
-- The grammar is the usual one for sums and products:
--
--     expr   ::= expr '+' term | expr '-' term | term
--     term   ::= term '*' factor | factor
--     factor ::= '(' expr ')' | digits
--
-- Each rule with a functional pattern, such as
--
--     expr (l ++ "+" ++ r) = Add (expr l) (term r)
--
-- matches every way to split the input around a '+'.  A split whose parts do
-- not parse fails, so only the well-formed parse survives.  There is no lexer
-- and there are no parser combinators.

import Data.Char
import Data.List

data Expr = Num Int | Add Expr Expr | Sub Expr Expr | Mul Expr Expr
  deriving Show

-- An expression is a sum or a difference whose right operand is a term, or a
-- single term.  The left operand is an expression again, so a run of
-- operators associates to the left.
expr :: String -> Expr
expr (l ++ "+" ++ r) = Add (expr l) (term r)
expr (l ++ "-" ++ r) = Sub (expr l) (term r)
expr t               = term t

-- A term is a product whose right operand is a factor, or a single factor.
-- The operands of a product are never sums, so '*' binds tighter than '+'
-- and '-'.
term :: String -> Expr
term (l ++ "*" ++ r) = Mul (term l) (factor r)
term f               = factor f

-- A factor is an expression in parentheses or a non-empty run of digits.
factor :: String -> Expr
factor ('(' : s) | last s == ')' = expr (init s)
factor ds | not (null ds) && all isDigit ds = Num (foldl addDigit 0 ds)
  where addDigit a d = 10 * a + ord d - ord '0'

-- The value of a parse tree.
eval :: Expr -> Int
eval (Num n)   = n
eval (Add a b) = eval a + eval b
eval (Sub a b) = eval a - eval b
eval (Mul a b) = eval a * eval b
