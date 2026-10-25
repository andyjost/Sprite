------------------------------------------------------------------------------
-- Library with operations to encapsulate search, i.e., to return all or
-- some values of an expression containing non-deterministic computations
-- in a data strcuture, as I/O operations in order to make the results
-- dependend on the external world, e.g., the schedule for non-determinism.
--
-- To encapsulate search in non-I/O computations, one can use
-- set functions (see module `Control.Search.SetFunctions`).
--
-- Author : Michael Hanus
-- Version: October 2026
------------------------------------------------------------------------------

-- Sprite uses weak native capsules, rather than the strong encapsulation
-- described by the upstream interface: free variables are not enumerated
-- inside, and argument nondeterminism stays outside. DFS is advisory; all
-- operations use Sprite's fair scheduler and value order. See Unsafe.
module Control.Search.AllValues
  ( getAllValues, getAllValuesDFS, getOneValue, getOneValueDFS, getAllFailures )
 where

import Control.Search.Unsafe

------------------------------------------------------------------------------

-- | Gets all values of an expression (similarly to Prolog's `findall`).
-- Conceptually, the value is computed on a copy of the expression,
-- i.e., the evaluation of the expression does not share any results.
--
-- The strategy to search for all values depends on the Curry system:
--
-- * PAKCS uses a depth-first search strategy and computes all values at once,
-- * KiCS2 uses a breadth-first search strategy and computes all values lazily.
-- * Curry2Go uses a fair search strategy and computes all values lazily.
--
--   In PAKCS, the evaluation suspends as long as the expression
--   or its computed value contain unbound variables.
getAllValues :: a -> IO [a]
getAllValues e = return (allValues e)

-- | Gets all values of an expression.
-- This operation is similar to 'getAllValues' but uses a depth-first search
-- strategy (if available).
-- Thus, it could be more efficient than 'getAllValues' but it might
-- not terminate (instead of computing of all values) if the search space
-- is infinite.
getAllValuesDFS :: a -> IO [a]
getAllValuesDFS e = return (allValuesDFS e)

-- | Gets one value of an expression or `Nothing`
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
getOneValue :: a -> IO (Maybe a)
getOneValue x = return (oneValue x)

-- | Gets one value of an expression or `Nothing`
-- if the expression has no value.
-- This operation is similar to 'getOneValue' but uses a depth-first search
-- strategy (if available).
-- Thus, it could be more efficient than 'getOneValue' but it might not terminate
-- (instead of computing of value) if the search space is infinite.
getOneValueDFS :: a -> IO (Maybe a)
getOneValueDFS x = return (oneValueDFS x)

-- | Returns a list of values that do not satisfy a given constraint.
-- As a simple example, the expression
--
--     getAllFailures ([] ? [1] ? [2]) (\xs -> head xs =:= 1)
--
-- evaluates to `[[], [2]]`.
getAllFailures :: a           -- ^ an expression 'e' (e.g., a generator
                              --   evaluable to various values)
               -> (a -> Bool) -- ^ a constraint 'c' that should not be satisfied
               -> IO [a]      -- ^ list of all values of `e`
                              --   such that `(c e)` is not provable
getAllFailures generator test = do
  xs <- getAllValues generator
  failures <- mapM (naf test) xs
  return $ concat failures

-- (naf c x) returns [x] if (c x) fails, and [] otherwise.
naf :: (a -> Bool) -> a -> IO [a]
naf c x = getOneValue (c x) >>= return . maybe [x] (const [])

------------------------------------------------------------------------------
