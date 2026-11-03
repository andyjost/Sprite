------------------------------------------------------------------------------
-- | Library with operations to encapsulate search, i.e., to return all or
-- some values of an expression containing non-deterministic computations
-- in a data structure.
-- Note that these operations are not fully declarative, i.e.,
-- the results depend on the order of evaluation and program rules.
-- This is due to the fact that the search operators work on a copy
-- of the current expression to be encapsulated.
-- The potential problems of this method are discussed in this paper:
--
-- > B. Brassel, M. Hanus, F. Huch:
-- > Encapsulating Non-Determinism in Functional Logic Computations
-- > Journal of Functional and Logic Programming, No. 6, EAPLS, 2004
--
-- There are newer and better approaches the encapsulate search,
-- in particular, set functions (see module `Control.Search.SetFunctions`)
-- which should be used.
--
-- Author : Michael Hanus
-- Version: October 2026
------------------------------------------------------------------------------
-- Sprite compatibility: the upstream interface describes strong search,
-- enumerating free variables inside the expression. Sprite uses weak native
-- capsules: free variables are not enumerated inside, and argument choices
-- stay outside. DFS names are advisory; scheduling and order are Sprite's.
module Control.Search.Unsafe
  (allValues, allValuesDFS, oneValue, oneValueDFS, someValue, isFail
  , rewriteAll, rewriteSome) where

import qualified Control.SetFunctions as Native

allValues :: a -> [a]
allValues e = Native.valuesOf (Native.evalS (Native.exprS e))

allValuesDFS :: a -> [a]
allValuesDFS e = allValues e

oneValue :: a -> Maybe a
oneValue e = first (allValues e)
 where
  first [] = Nothing
  first (x:_) = Just x

oneValueDFS :: a -> Maybe a
oneValueDFS e = oneValue e

someValue :: a -> a
someValue e = case oneValue e of
  Nothing -> failed
  Just x -> x

isFail :: a -> Bool
isFail e = case oneValue e of
  Nothing -> True
  Just _ -> False

-- Weak rewriting uses the same native capsule as allValues. Unlike PAKCS,
-- outside-variable demands escape: rewriteAll (not x), for an outside free
-- Bool x, gives [False] with x=True and [True] with x=False.
rewriteAll :: a -> [a]
rewriteAll e = allValues e

-- Weak rewriting takes only the first capsule value, without demanding its
-- tail. Unlike PAKCS, outside-variable demands escape: rewriteSome (not x),
-- for an outside free Bool x, gives Just False with x=True and Just True
-- with x=False.
rewriteSome :: a -> Maybe a
rewriteSome e = oneValue e
