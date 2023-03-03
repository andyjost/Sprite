------------------------------------------------------------------------------
-- Example for the use of functional pattern to specify program transformations
--
-- More details are described in:
--
-- Sergio Antoy, Michael Hanus:
-- Declarative Programming with Function Patterns
-- Proceedings of the International Symposium on Logic-based Program Synthesis
-- and Transformation (LOPSTR'05), Springer LNCS 3901, pp. 6-22
------------------------------------------------------------------------------

import Control.SetFunctions

----------------------------------------------------------
-- Representation of arithmetic expressions:
data Exp = Lit Int
         | Var String
         | Add Exp Exp
         | Mul Exp Exp

-- Example: representation of "1 * x + 0"
exp1 = Mul (Lit 1) (Add (Var "x") (Lit 0))

-- We define a position in an expression as a sequence of integers (1 or 2):
type Pos = [Int]

-- (replace e1 p e2): replace in e1 the subterm at position p by e2
replace :: Exp -> Pos -> Exp -> Exp
replace _ [] x = x
replace (Add l r) (1:p) x = Add (replace l p x) r
replace (Add l r) (2:p) x = Add l (replace r p x)
replace (Mul l r) (1:p) x = Mul (replace l p x) r
replace (Mul l r) (2:p) x = Mul l (replace r p x)

-- (evalTo x): some expression which can be simplified to x
evalTo :: Exp -> Exp
evalTo x = Add (Lit 0) x
         ? Add x (Lit 0)
         ? Mul (Lit 1) x
         ? Mul x (Lit 1)

-- Now we can define a simplifaction step exploiting functional patterns:
simplify :: Exp -> Exp
simplify (replace e p (evalTo x)) = replace e p x

main0 = simplify exp1  --> Add (Var "x") (Lit 0) | Mul (Lit 1) (Var "x")

-- Apply simplifcation steps as long as possible:
simplifyAll :: Exp -> Exp
simplifyAll exp =
  if isEmpty simpExps then exp else simplifyAll (selectValue simpExps)
 where
   simpExps = (set1 simplify) exp

main1 = simplifyAll exp1  --> Var "x"

-- Get some variable in an arithmetic expression:
varInExp :: Exp -> String
varInExp (replace _ _ (Var x)) = x

-- Example: "y + 1 * x + 0"
exp2 = Add (Var "y") exp1

-- Get all variables in an expression by exploiting set functions:
allVars :: Exp -> [String]
allVars e = sortValues ((set1 varInExp) e)

main2 = allVars exp2 --> ["x","y"]


main = (main0, main1, main2)
