-- Overload resolution over the type algebra of CxxType, driven from Python.
--
-- Every goal takes an overload set, a class hierarchy and a call, all built
-- in Python, and returns text.  The search lives in CxxOverload: viable
-- picks a candidate and a conversion sequence for each argument
-- non-deterministically, and a set function collects the viable set.  The
-- last goal turns the question round.  A free variable stands for the
-- argument type, a bounded generator enumerates the types, and each type
-- is tested for an ambiguous call.

module Overloads where

import Control.SetFunctions
import Data.List (intercalate, nub, sort)
import CxxLimits
import CxxType
import CxxOverload

-- The viable candidates of a call with the rank of each argument.
viableLine :: Hierarchy -> [Candidate] -> [Type] -> String
viableLine h cands args = showViables (viables h cands args)

-- The result of overload resolution for a call.
resultLine :: Hierarchy -> [Candidate] -> [Type] -> String
resultLine h cands args = showResolution (resolve h cands args)

-- (d) The inverse question: an argument type of depth at most n that makes
-- a call of the overload set with one argument ambiguous.  The free
-- variable t is the unknown.  The first equation binds it to one type of
-- the bounded generator; the second is the question.  Every solution is
-- one value.
--
-- The operator $## evaluates t to normal form before the question sees it.
-- The question runs a set function, and a set function must get the value
-- of t, not the variable: in this version of Sprite a set function applied
-- to a variable that a choice bound sees the binding of the first
-- alternative in every branch, and a choice inside the argument multiplies
-- the work of the set function.
ambiguousArg :: Int -> [Candidate] -> Type
ambiguousArg n cands
  | t =:= anyType n && (ambiguousCall cands $## t) = t
  where t free

-- Whether the call of the overload set with the one argument is ambiguous.
ambiguousCall :: [Candidate] -> Type -> Bool
ambiguousCall cands a = isAmbiguous (resolve [] cands [a])

-- The solutions in one line: the count of the types, then the distinct
-- prvalue types that the lvalue transformations leave, sorted.  The
-- generator yields each type once, so the solutions are distinct types.
ambiguousArgs :: Int -> [Candidate] -> String
ambiguousArgs n cands =
  showNat (length types) ++ " types; after the lvalue transformations, "
  ++ showNat (length prvalues) ++ ": " ++ intercalate ", " (map showCxx prvalues)
  where
    types    = sortValues (set2 ambiguousArg n cands)
    prvalues = nub (sort (map prvalue types))
