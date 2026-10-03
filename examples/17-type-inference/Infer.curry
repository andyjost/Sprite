-- Type inference by unification.
--
-- A small typed lambda calculus with integers, Booleans, addition, and a
-- conditional.  The function infer computes the type of a term.  It uses two
-- features of functional logic programming:
--
--   * A free variable stands for a type that is not yet known.  The rule for
--     Lam gives the bound variable the fresh type a and infers the body under
--     that assumption.
--
--   * The constraint =:= is unification.  The rule for App requires the type
--     of the function to be Fun (type of the argument) r, where r is free.
--     Unification binds r to the result type, and it may also bind variables
--     inside the type of the function or of the argument.
--
-- A term with no type has no value: the guard of some rule fails and the
-- whole computation fails.  Failure is not an error in Curry.

data Type = TInt | TBool | Fun Type Type
  deriving Show

data Term = Var String
          | Lam String Term
          | App Term Term
          | Lit Int
          | BoolLit Bool
          | If Term Term Term
          | Add Term Term

-- The type of a term under an environment that gives the type of every
-- variable in scope.  Each rule reads like the typing rule it implements.
infer :: [(String, Type)] -> Term -> Type
infer env (Var x) = case lookup x env of
  Just t -> t
infer _ (Lit _) = TInt
infer _ (BoolLit _) = TBool
infer env (Lam x b) = Fun a (infer ((x, a) : env) b)
  where a free
infer env (App f x) | infer env f =:= Fun (infer env x) r = r
  where r free
infer env (If c t e)
  | infer env c =:= TBool & infer env t =:= ty & infer env e =:= ty = ty
  where ty free
infer env (Add a b) | infer env a =:= TInt & infer env b =:= TInt = TInt
