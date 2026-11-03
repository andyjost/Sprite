------------------------------------------------------------------------------
--- Library for converting ground terms to strings and vice versa.
---
--- Remark: The `Data` type class constraint is removed for KiCS2
--- since this causes a memory leak (due to the non-deterministic method
--- `aValue`) but it is not used in the implementation.
---
--- @author Michael Hanus
--- @version April 2025
------------------------------------------------------------------------------
{-# LANGUAGE CPP #-}

module ReadShowTerm ( showTerm, readsUnqualifiedTerm, readUnqualifiedTerm )
 where

import Data.Char ( isSpace )

--- Transforms a ground(!) data term into a string representation
--- in standard prefix notation.
--- Thus, `showTerm` suspends until its argument is ground.
--- This function is similar to the prelude function `show`
--- but can read the string back with `readUnqualifiedTerm`
--- (provided that the constructor names are unique without the module
--- qualifier).
#ifdef __KICS2__
showTerm :: a -> String
#elif  __KMCC__ > 0
showTerm :: a -> String
#else
showTerm :: Data a => a -> String
#endif
showTerm x = prim_showTerm $## x

prim_showTerm :: _ -> String
prim_showTerm external


--- Transform a string containing a data term in standard prefix notation
--- without module qualifiers into the corresponding data term.
--- The first argument is a non-empty list of module qualifiers
--- that are tried to prefix the constructor in the string
--- in order to get the qualified constructors
--- (that must be defined in the current program!).
--- In case of a successful parse, the result is a one element list
--- containing a pair of the data term and the remaining unparsed string.

#ifdef __KICS2__
readsUnqualifiedTerm :: [String] -> String -> [(a,String)]
#elif  __KMCC__ > 0
readsUnqualifiedTerm :: [String] -> String -> [(a,String)]
#else
readsUnqualifiedTerm :: Data a => [String] -> String -> [(a,String)]
#endif
readsUnqualifiedTerm [] _ =
  error "ReadShowTerm.readsUnqualifiedTerm: list of module prefixes is empty"
readsUnqualifiedTerm (prefix:prefixes) s =
  readsUnqualifiedTermWithPrefixes (prefix:prefixes) s

#ifdef __KICS2__
readsUnqualifiedTermWithPrefixes :: [String] -> String -> [(a,String)]
#elif  __KMCC__ > 0
readsUnqualifiedTermWithPrefixes :: [String] -> String -> [(a,String)]
#else
readsUnqualifiedTermWithPrefixes :: Data a => [String] -> String -> [(a,String)]
#endif
readsUnqualifiedTermWithPrefixes prefixes s =
  (prim_readsUnqualifiedTerm $## prefixes) $## s

prim_readsUnqualifiedTerm :: [String] -> String -> [(_,String)]
prim_readsUnqualifiedTerm external

--- Transforms a string containing a data term in standard prefix notation
--- without module qualifiers into the corresponding data term.
--- The first argument is a non-empty list of module qualifiers
--- that are tried to prefix the constructor in the string
--- in order to get the qualified constructors
--- (that must be defined in the current program!).
---
--- Example: `readUnqualifiedTerm ["Prelude"] "Just 3"` evaluates to `(Just 3)`

#ifdef __KICS2__
readUnqualifiedTerm :: [String] -> String -> a
#elif  __KMCC__ > 0
readUnqualifiedTerm :: [String] -> String -> a
#else
readUnqualifiedTerm :: Data a => [String] -> String -> a
#endif
readUnqualifiedTerm prefixes s = case result of
  [(term,tail)]
     -> if all isSpace tail
          then term
          else error $ "ReadShowTerm.readUnqualifiedTerm: no parse, " ++
                       "unmatched string after term: " ++ tail
  [] ->  error "ReadShowTerm.readUnqualifiedTerm: no parse"
  _  ->  error "ReadShowTerm.readUnqualifiedTerm: ambiguous parse"
 where
  result = readsUnqualifiedTerm prefixes s
