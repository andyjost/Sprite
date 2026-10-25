import Control.Search.SetFunctions

-- the type of simple symbolic arithmetic expressions
data Exp = Lit Int
         | Var [Char]
         | Add Exp Exp
         | Mul Exp Exp

-- generate an expression containing the argument as a subexpression
withSub :: Exp -> Exp
withSub exp = exp
            ? op (withSub exp) unknown
            ? op unknown (withSub exp)
   where op = Add ? Mul

-- get the identifier of a variable occurring in the argument
varOf :: Exp -> String
varOf (withSub (Var v)) = v

-- sample expression
sample :: Exp
sample = Add (Var "x") (Mul (Lit 1) (Var "y"))

-- get the set of the idenfiers occurring in the argument
main :: [String]
main = sortValues (set1 varOf sample)
