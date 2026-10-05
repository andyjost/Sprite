-- Template argument deduction over the type algebra of CxxType.
--
-- Every goal takes concrete types, built in Python, and returns text.  A
-- template parameter is a Curry free variable.  A function template names
-- its template parameters, and a pattern refers to one as the class of its
-- name: Class "T" [] is T.  deduceCall of CxxType replaces each name by a
-- fresh free variable and unifies the parameter patterns with the argument
-- types.  The bindings of the variables are the deduced template arguments.
-- A set function collects the bindings, so that a failed deduction is an
-- empty set and not a failed goal.

module Deduction where

import Control.SetFunctions
import Data.List (intercalate)
import CxxLimits
import CxxType

-- (a), (b) The bindings of the template parameters names of a function
-- template with the parameters params, for a call with the argument types
-- args.  An argument type LRef t is an lvalue of type t, RRef t an xvalue,
-- and a bare t a prvalue.
call :: [String] -> [Param] -> [Type] -> String
call names params args = report (sortValues (set3 bindCall names params args))

bindCall :: [String] -> [Param] -> [Type] -> String
bindCall names params args = showSubst (deduceCall names params args)

-- The bindings in one line: "T = int, U = char".
showSubst :: Subst -> String
showSubst env = intercalate ", " [n ++ " = " ++ showCxx t | (n, t) <- env]

-- The function parameters of a template in C++ spelling: "f(T const&)".
signature :: String -> [Param] -> String
signature f params = f ++ "(" ++ intercalate ", " (map showParam params) ++ ")"

showParam :: Param -> String
showParam param = case param of
  ByValue p -> showCxx p
  ByLRef p  -> showCxx (LRef p)
  ByRRef p  -> showCxx (RRef p)

-- (c) Partial ordering.  The most specialized of the partial
-- specializations specs of a class template S for the target.  Each
-- specialization is named by its pattern.
ordering :: [Template] -> Type -> String
ordering specs target = showChoice (mostSpecialized (map named specs) target)

named :: Template -> (String, Template)
named tmpl = case tmpl of
  Template _ pat -> ("S<" ++ showCxx pat ++ ">", tmpl)

specName :: Template -> String
specName tmpl = fst (named tmpl)

showChoice :: Choice -> String
showChoice c = case c of
  Chosen n -> "unique: " ++ n
  Tied ns  -> "ambiguous: " ++ intercalate ", " ns
  NoMatch  -> "no match"

-- (d) The inverse questions.  The free variable t is the unknown type.  The
-- first equation binds it to one type of the bounded generator; the second
-- is the question.  Every solution is one value, and every type is one
-- solution at most, because the generator yields each type once.

-- The types of depth at most n whose decay is the target.
decaysTo :: Int -> Type -> Type
decaysTo n target | t =:= anyType n && decay t =:= target = t
  where t free

-- The solutions in one line, sorted.
inverseDecay :: Int -> Type -> String
inverseDecay n target =
  intercalate ", " (sortValues (set2 decaysToText n target))

decaysToText :: Int -> Type -> String
decaysToText n target = showCxx (decaysTo n target)

-- The types of depth at most n from which a template with the one template
-- parameter T and the function parameters params deduces T = wanted.
-- deduceCall on a bound type has one value, the binding of T, and the
-- second equation compares it with the answer.
deducesTo :: Int -> [Param] -> Type -> Type
deducesTo n params wanted
  | t =:= anyType n && deduceCall ["T"] params [t] =:= [("T", wanted)] = t
  where t free

inverseDeduction :: Int -> [Param] -> Type -> String
inverseDeduction n params wanted =
  intercalate ", " (sortValues (set3 deducesToText n params wanted))

deducesToText :: Int -> [Param] -> Type -> String
deducesToText n params wanted = showCxx (deducesTo n params wanted)

-- The sorted bindings, or the failure, in one line.
report :: [String] -> String
report bs = case bs of
  []      -> "no deduction"
  (_ : _) -> intercalate " | " bs
