module Canon where
import Control.SetFunctions (set1, set2, isEmpty, chooseValue, sortValues)
import Data.List (nub, sort)

data Expr = Const Int | Var String | Add Expr Expr | Mul Expr Expr | Transpose Expr
  deriving (Eq, Ord)
-- The rules.  A rule has no value on a term it does not rewrite; that absence is the match test.
addZero (Add a (Const 0)) = a
mulOne (Mul a (Const 1)) = a
mulZero (Mul _ (Const 0)) = Const 0
fold (Add (Const m) (Const n)) = Const (m + n)
fold (Mul (Const m) (Const n)) = Const (m * n)
constRight (Add (Const c) a) | notConst a = Add a (Const c)
constRight (Mul (Const c) a) | notConst a = Mul a (Const c)
reassoc (Add (Add a (Const m)) (Const n)) = Add a (Const (m + n))
reassoc (Mul (Mul a (Const m)) (Const n)) = Mul a (Const (m * n))
twice (Mul a (Const 2)) = Add a a
transpose (Transpose (Transpose a)) = a
transpose (Transpose (Const c)) = Const c
notConst e = case e of Const _ -> False; _ -> True
rules = [("addZero", addZero), ("mulOne", mulOne), ("mulZero", mulZero), ("fold", fold),
  ("constRight", constRight), ("reassoc", reassoc), ("twice", twice), ("transpose", transpose)]
ruleNames = map fst rules

-- One rewrite step, by any rule at any position: the name of the rule and the result.
step :: [(String, Expr -> Expr)] -> Expr -> (String, Expr)
step rs e = atRoot rs e ? inside rs e
atRoot rs e = case anyOf rs of (name, rule) -> (name, rule e)
inside rs (Add a b) = under rs (\a' -> Add a' b) a ? under rs (Add a) b
inside rs (Mul a b) = under rs (\a' -> Mul a' b) a ? under rs (Mul a) b
inside rs (Transpose a) = under rs Transpose a
under rs k a = case step rs a of (n, a') -> (n, k a')

-- One rewrite order to a normal form, a term with no step, within 32 steps.  The set
-- of steps exists for isEmpty; chooseValue makes each step a value again.
normalize :: [(String, Expr -> Expr)] -> Expr -> ([String], Expr, Bool)
normalize rs e = go (32 :: Int) e
  where go fuel t = let steps = set2 step rs t in
          if isEmpty steps then ([], t, True)
          else if fuel == 0 then ([], t, False)
          else case chooseValue steps of
            (n, t') -> case go (fuel - 1) t' of (ns, nf, ok) -> (n : ns, nf, ok)
-- Every rewrite order under the named rules, one entry per order, sorted.
normalForms names e = sortValues (set2 normalize active e)
  where active = [r | r@(name, _) <- rules, name `elem` names]

-- The terms of depth at most d over x, 2 and 3, and those with more than one normal form.
terms d = Var "x" ? Const (2 ? 3) ? deeper
  where deeper | d > 0 = Add (terms (d - 1)) (terms (d - 1))
                       ? Mul (terms (d - 1)) (terms (d - 1)) ? Transpose (terms (d - 1))
census d names = (length ts, [(t, forms) | t <- ts, let forms = distinct t, length forms > 1])
  where ts = sortValues (set1 terms d)
        distinct t = nub (sort [form | (_, form, True) <- normalForms names t])

render (Const n) = show n
render (Var v) = v
render (Add a b) = sub a ++ " + " ++ sub b
render (Mul a b) = sub a ++ " * " ++ sub b
render (Transpose a) = "T " ++ sub a
sub e = case e of Const _ -> render e; Var _ -> render e; _ -> "(" ++ render e ++ ")"
