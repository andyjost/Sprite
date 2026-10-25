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
{-# LANGUAGE CPP #-}

module Control.Search.Unsafe
  ( allValues, allValuesDFS, oneValue, oneValueDFS, someValue, isFail
  , rewriteAll, rewriteSome
  ) where

#ifdef __KICS2__
import qualified Control.Search.SearchTree as ST
#endif

------------------------------------------------------------------------------

-- | Returns all values of an expression.
-- Conceptually, the value is computed on a copy of the expression,
-- i.e., the evaluation of the expression does not share any results.
--
-- The strategy to search for all values depends on the Curry system:
--
-- * PAKCS uses a depth-first search strategy and computes all values at once,
-- * KiCS2 uses a breadth-first search strategy and computes all values lazily.
-- * Curry2Go uses a fair search strategy and computes all values lazily.
--
-- In PAKCS, the evaluation suspends as long as the expression
-- or its computed value contain unbound variables.
--
-- Note that this operation is not purely declarative since the ordering
-- of the computed values depends on the ordering of the program rules.
allValues :: a -> [a]
#ifdef __KICS2__
allValues e = ST.allValuesBFS (ST.someSearchTree e)
#else
allValues external
#endif

-- | Returns all values of an expression.
-- This operation is similar to 'allValues' but uses a depth-first search
-- strategy (if available).
-- Thus, it could be more efficient than 'allValues' but it might
-- not terminate (instead of computing of all values) if the search space
-- is infinite.
allValuesDFS :: a -> [a]
#ifdef __KICS2__
allValuesDFS e = ST.allValuesDFS (ST.someSearchTree e)
#elif defined(__PAKCS__)
allValuesDFS x = allValues x  -- PAKCS supports only depth-first search
#elif defined(__CURRY2GO__)
allValuesDFS x = allValues x  -- TODO: implement as external operation
#else
allValuesDFS external
#endif

-- | Returns just one value for an expression or `Nothing`
-- if the expression has no value.
-- Conceptually, the value is computed on a copy of the expression,
-- i.e., the evaluation of the expression does not share any results.
--
-- The strategy to search for a value depends on the Curry system:
--
-- * PAKCS uses a depth-first search strategy,
-- * KiCS2 uses a breadth-first search strategy, and
-- * Curry2Go uses a fair search strategy.
--
-- In PAKCS, the evaluation suspends as long as the expression
-- or its computed value contain unbound variables.
--
-- Note that this operation is not purely declarative since
-- the computed value depends on the ordering of the program rules.
-- Thus, this operation should be used only if the expression
-- has at most one value.
oneValue :: a -> Maybe a
#ifdef __KICS2__
oneValue x =
  let vals = ST.allValuesWith ST.bfsStrategy (ST.someSearchTree x)
  in (if null vals then Nothing else Just (head vals))
#else
oneValue external
#endif

-- | Returns just one value for an expression or `Nothing`
-- if the expression has no value.
-- This operation is similar to 'oneValue' but uses a depth-first search
-- strategy (if available).
-- Thus, it could be more efficient than 'oneValue' but it might not terminate
-- (instead of computing of value) if the search space is infinite.
oneValueDFS :: a -> Maybe a
#ifdef __KICS2__
oneValueDFS x =
  let vals = ST.allValuesWith ST.dfsStrategy (ST.someSearchTree x)
  in (if null vals then Nothing else Just (head vals))
#elif defined(__PAKCS__)
oneValueDFS x = oneValue x  -- PAKCS supports only depth-first search
#elif defined(__CURRY2GO__)
oneValueDFS x = oneValue x  -- TODO: implement as external operation
#elif defined(__KMCC__)
oneValueDFS x = oneValue x  -- TODO: implement as external operation
#else
oneValueDFS external
#endif

-- | Returns some value for an expression.
-- If the expression has no value, the computation fails.
-- Conceptually, the value is computed on a copy of the expression,
-- i.e., the evaluation of the expression does not share any results.
--
-- In PAKCS, the evaluation suspends as long as the expression
-- or its computed value contain unbound variables.
--
-- Note that this operation is not purely declarative since
-- the computed value depends on the ordering of the program rules.
-- Thus, this operation should be used only if the expression
-- has a single value.
someValue :: a -> a
someValue x = case oneValue x of Just v  -> v
                                 Nothing -> failed

-- | Does the computation of the argument to a value fail?
-- Thus, `isFail e` returns `True` if the expression `e`
-- has no value. For instance, `isFail (head [])` evaluates to `True`.
--
-- Conceptually, the argument is evaluated on a copy, i.e.,
-- even if the computation does not fail, it has not been evaluated.
isFail :: a -> Bool
isFail x = case oneValue x of Nothing -> True
                              Just _  -> False

------------------------------------------------------------------------------
-- | Gets all values computable by term rewriting.
-- In contrast to `allValues`, this operation does not wait
-- until all "outside" variables are bound to values,
-- but it returns all values computable by term rewriting
-- and ignores all computations that requires bindings for outside variables.
rewriteAll :: a -> [a]
#ifdef __PAKCS__
rewriteAll external
#else
rewriteAll _ = error "Control.Search.Unsafe.rewriteAll: not yet implemented"
#endif

-- | Similarly to 'rewriteAll' but returns only some value computable
-- by term rewriting. Returns `Nothing` if there is no such value.
rewriteSome :: a -> Maybe a
#ifdef __PAKCS__
rewriteSome external
#else
rewriteSome _ = error "Control.Search.Unsafe.rewriteSome: not yet implemented"
#endif

------------------------------------------------------------------------------
