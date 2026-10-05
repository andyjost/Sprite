-- A bounded model check of the type traits of CxxType.
--
-- The module has two parts:
--
--   * the properties: each one states that a trait of the library agrees
--     with a definition of the standard, written out in other traits; one
--     property checks a trait that is wrong on purpose;
--   * the driver: for one property, a set function collects the types for
--     which the property is False, and another set function counts the
--     types.
--
-- The types come from the bounded generator anyType of CxxType, which
-- enumerates every well-formed type of the algebra up to a depth, one type
-- per value.  The generator builds the types by category and calls no
-- trait, so the check examines the traits and nothing else.
--
-- The search is narrowing.  A free variable t is the unknown type.  The
-- guard t =:= anyType n binds it to one value of the generator, and
-- not (p t) keeps the binding when the property p fails for it.  Every
-- solution is one counterexample.
--
-- The check is bounded: it says nothing about the types beyond the depth,
-- and it covers only the shapes the generator builds.  The model is a
-- simplification of the C++ type system: it has no enumerations, unions,
-- wide character types, noexcept or ref-qualified functions, and no
-- non-type template parameters.  Every top-level function has a type
-- signature.

module CxxCheck where

import Control.SetFunctions
import Data.List (intercalate)
import CxxLimits
import CxxType

-- The properties --------------------------------------------------------------
--
-- A property is a function from a type to Bool.  Each one puts a definition
-- of the standard, written out in other traits, beside the trait of the
-- library.  The comments name the section of the standard.

-- [basic.types.general], [meta.unary.comp]: a scalar type is an arithmetic
-- type, an enumeration, a pointer, a pointer to member, std::nullptr_t, or a
-- cv-qualified version of one of these.  The model has no enumerations.
scalarByDefinition :: Type -> Bool
scalarByDefinition t = is_arithmetic t || is_pointer t || is_member_pointer t
                       || is_null_pointer t

propScalar :: Type -> Bool
propScalar t = is_scalar t == scalarByDefinition t

-- [basic.fundamental]: the fundamental types are the arithmetic types, void
-- and std::nullptr_t.
propFundamental :: Type -> Bool
propFundamental t =
  is_fundamental t == (is_arithmetic t || is_void t || is_null_pointer t)

-- [basic.types.general]: an object type is a type that is not a function
-- type, not a reference type and not cv void.  The library takes that
-- definition.  The property checks it against the other reading of the same
-- section: the object types are the scalar types, the arrays and the classes.
propObject :: Type -> Bool
propObject t = is_object t == (is_scalar t || is_array t || is_class t)

-- [meta.unary.cat]: whether each primary type category holds for a type,
-- in the order of the table of the standard.  The model has no enumerations
-- or unions, and one trait covers the pointers to data members and to
-- member functions.
primaryCategories :: Type -> [Bool]
primaryCategories t =
  [ is_void t, is_null_pointer t, is_integral t, is_floating_point t, is_array t
  , is_pointer t, is_lvalue_reference t, is_rvalue_reference t
  , is_member_pointer t, is_class t, is_function t ]

-- [meta.unary.cat]: for any type, exactly one primary type category holds,
-- and the same one for the cv-qualified type.  The terms Const t and
-- Volatile t are not normalized here: the traits normalize their arguments,
-- and that is part of what is checked.
propCategory :: Type -> Bool
propCategory t =
  length (filter id cs) == 1 && primaryCategories (Const t) == cs
                             && primaryCategories (Volatile t) == cs
  where
    cs = primaryCategories t

-- [meta.trans.other]: decay yields a type that decay leaves alone.
propDecayTwice :: Type -> Bool
propDecayTwice t = decay d == d
  where
    d = decay t

-- [meta.trans.ref], [meta.trans.other]: for an object type, remove_cvref
-- takes the added reference off again, and the qualifiers with it.
propCvref :: Type -> Bool
propCvref t =
  not (is_object t) || remove_cvref (add_lvalue_reference t) == remove_cv t

-- The wrong trait: an is_scalar that forgets the pointers to members.  It
-- lives here, not in the library, so that the search has something to find.
is_scalar_wrong :: Type -> Bool
is_scalar_wrong t = is_arithmetic t || is_pointer t || is_null_pointer t

propWrongScalar :: Type -> Bool
propWrongScalar t = is_scalar_wrong t == scalarByDefinition t

-- The properties by name, with the statement that the report prints.
properties :: [(String, (String, Type -> Bool))]
properties =
  [ ("scalar",
      ("is_scalar t == is_arithmetic t || is_pointer t || is_member_pointer t"
       ++ " || is_null_pointer t",
       propScalar))
  , ("fundamental",
      ("is_fundamental t == is_arithmetic t || is_void t || is_null_pointer t",
       propFundamental))
  , ("object",
      ("is_object t == is_scalar t || is_array t || is_class t",
       propObject))
  , ("category",
      ("exactly one primary type category holds for t, and the same one for"
       ++ " t const and t volatile",
       propCategory))
  , ("decay_twice",
      ("decay (decay t) == decay t",
       propDecayTwice))
  , ("cvref",
      ("remove_cvref (add_lvalue_reference t) == remove_cv t, for an object"
       ++ " type t",
       propCvref))
  , ("wrong_scalar",
      ("is_scalar_wrong t == is_arithmetic t || is_pointer t"
       ++ " || is_member_pointer t || is_null_pointer t,"
       ++ " where is_scalar_wrong forgets the pointers to members",
       propWrongScalar))
  ]

-- The statement and the function of a property.  An unknown name has no
-- value.
property :: String -> (String, Type -> Bool)
property name = case lookup name properties of
  Just p -> p

-- The driver ------------------------------------------------------------------

-- A counterexample of the named property among the types of depth at most
-- n, as its depth and its text in C++ syntax, so that a sort puts the
-- simplest first.  The free variable t is the unknown type.  The first
-- equation of the guard binds it to one value of the generator; the second
-- keeps the binding when the property is False for it.  Every solution is
-- one value.
counterexample :: Int -> String -> (Int, String)
counterexample n name | t =:= anyType n && not (p t) = (depth t, showCxx t)
  where
    (_, p) = property name
    t free

-- The counterexamples of a property, by depth and then by name.
counterexamples :: Int -> String -> [String]
counterexamples n name = map snd (sortValues (set2 counterexample n name))

-- The number of types of depth at most n: the values of the generator,
-- counted by a set function.
countTypes :: Int -> Int
countTypes n = foldValues (+) 0 (mapValues (\_ -> 1) (set1 anyType n))

-- The first line of the report.
header :: Int -> String
header n = "Every type of depth at most " ++ show n ++ ": "
           ++ show (countTypes n) ++ " types."

-- The report for one property: its name and statement, then the count of
-- the counterexamples with the five simplest, or the count of the types
-- checked.
check :: Int -> String -> String
check n name = name ++ ": " ++ statement ++ "\n  " ++ verdict
  where
    (statement, _) = property name
    bad = counterexamples n name
    shown = take 5 bad
    verdict = if null bad
      then "no counterexample among " ++ show (countTypes n) ++ " types"
      else show (length bad) ++ " counterexamples, the " ++ show (length shown)
           ++ " simplest: " ++ intercalate ", " shown
