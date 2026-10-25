------------------------------------------------------------------------
-- | This module contains an implementation of set functions.
--
-- The general idea of set functions is described in:
--
-- > S. Antoy, M. Hanus: Set Functions for Functional Logic Programming
-- > Proc. 11th International Conference on Principles and Practice
-- > of Declarative Programming (PPDP'09), pp. 73-82, ACM Press, 2009
--
-- The general concept of set functions is as follows.
-- If `f` is an n-ary function, then `(setn f)` is a set-valued
-- function that collects all non-determinism caused by f (but not
-- the non-determinism caused by evaluating arguments!) in a set.
-- Thus, `(setn f a1 ... an)` returns the set of all
-- values of `(f b1 ... bn)` where `b1`,...,`bn` are values
-- of the arguments `a1`,...,`an` (i.e., the arguments are
-- evaluated "outside" this capsule so that the non-determinism
-- caused by evaluating these arguments is not captured in this capsule
-- but yields several results for `(setn...)`.
-- Similarly, logical variables occuring in `a1`,...,`an` are not bound
-- inside this capsule (in PAKCS they cause a suspension until
-- they are bound).
--
-- *Remark:*
-- Since there is no special syntax for set functions,
-- one has to write `(setn f)` for the set function of the
-- _n-ary top-level function_ `f`.
-- The correct usage of set functions is currently not checked by
-- the compiler, i.e., one can also write unintended uses
-- like `set0 ((+1) (1 ? 2))`.
-- In order to check the correct use of set functions,
-- it is recommended to apply the tool
-- [CurryCheck](https://cpm.curry-lang.org/pkgs/currycheck.html)
-- on Curry programs which reports illegal uses of set functions
-- (among other properties).
--
-- The set of values returned by a set function is represented
-- by an abstract type 'Values' on which several operations are
-- defined in this module. Actually, it is a multiset of values,
-- i.e., duplicates are not removed.
--
-- The handling of failures and nested occurrences of set functions
-- is not specified in the previous paper. Thus, a detailed description
-- of the semantics of set functions as implemented in this library
-- can be found in the paper
--
-- > J. Christiansen, M. Hanus, F. Reck, D. Seidel:
-- > A Semantics for Weakly Encapsulated Search in Functional Logic Programs
-- > Proc. 15th International Conference on Principles and Practice
-- > of Declarative Programming (PPDP'13), pp. 49-60, ACM Press, 2013
--
-- Note that the implementation of this library uses multisets
-- instead of sets. Thus, the result of a set function might
-- contain multiple values. From a declarative point of view,
-- this is not relevant. It has the advantage that equality
-- is not required on values, i.e., encapsulated values can also
-- be functional.
--
-- The PAKCS implementation of set functions has several restrictions,
-- in particular:
--
-- 1. The multiset of values is completely evaluated when demanded.
--    Thus, if it is infinite, its evaluation will not terminate
--    even if only some elements (e.g., for a containment test)
--    are demanded. However, for the emptiness test, at most one
--    value will be computed
-- 2. The arguments of a set function are strictly evaluated before
--    the set functions itself will be evaluated.
-- 3. If the multiset of values contains unbound variables,
--    the evaluation suspends.
--
-- Author : Michael Hanus, Fabian Reck
-- Version: October 2026
------------------------------------------------------------------------
module Control.Search.SetFunctions
  (set0, set1, set2, set3, set4, set5, set6, set7
  , set0With, set1With, set2With, set3With, set4With, set5With, set6With, set7With
  , Strategy, dfsStrategy, bfsStrategy, idsStrategy, idsStrategyWith, diagStrategy
  , Values, isEmpty, notEmpty, valueOf, choose, chooseValue, select, selectValue
  , getSomeValue, getSome, mapValues, foldValues, filterValues
  , minValue, maxValue, minValueBy, maxValueBy
  , values2list, printValues, sortValues, sortValuesBy
  ) where

import Control.SetFunctions (Values)
import qualified Control.SetFunctions as Native

-- Sprite facade. Values is the canonical Control.SetFunctions.Values,
-- represented by Values [a]. Multiplicities are retained. Nondeterminism
-- in the body is captured; nondeterminism in arguments stays outside.
-- Strategies (provided by KiCS2 in base) are advisory in Sprite. Every
-- strategy uses Sprite's fair scheduler and Sprite's value order.
data Strategy a = AdvisoryStrategy

dfsStrategy, bfsStrategy, idsStrategy, diagStrategy :: Strategy a
dfsStrategy = AdvisoryStrategy
bfsStrategy = AdvisoryStrategy
idsStrategy = AdvisoryStrategy
diagStrategy = AdvisoryStrategy

idsStrategyWith :: Int -> (Int -> Int) -> Strategy a
idsStrategyWith _ _ = AdvisoryStrategy

set0 :: b -> Values b
set0 external

set0With :: Strategy b -> b -> Values b
set0With _ f = Native.evalS (Native.exprS f)

set1 :: (a1 -> b) -> a1 -> Values b
set1 external

set1With :: Strategy b -> (a1 -> b) -> a1 -> Values b
set1With _ f x1 = set1 f x1

set2 :: (a1 -> a2 -> b) -> a1 -> a2 -> Values b
set2 external

set2With :: Strategy b -> (a1 -> a2 -> b) -> a1 -> a2 -> Values b
set2With _ f x1 x2 = set2 f x1 x2

set3 :: (a1 -> a2 -> a3 -> b) -> a1 -> a2 -> a3 -> Values b
set3 external

set3With :: Strategy b -> (a1 -> a2 -> a3 -> b) -> a1 -> a2 -> a3 -> Values b
set3With _ f x1 x2 x3 = set3 f x1 x2 x3

set4 :: (a1 -> a2 -> a3 -> a4 -> b) -> a1 -> a2 -> a3 -> a4 -> Values b
set4 external

set4With :: Strategy b -> (a1 -> a2 -> a3 -> a4 -> b)
            -> a1 -> a2 -> a3 -> a4 -> Values b
set4With _ f x1 x2 x3 x4 = set4 f x1 x2 x3 x4

set5 :: (a1 -> a2 -> a3 -> a4 -> a5 -> b) -> a1 -> a2 -> a3 -> a4 -> a5 -> Values b
set5 external

set5With :: Strategy b -> (a1 -> a2 -> a3 -> a4 -> a5 -> b)
            -> a1 -> a2 -> a3 -> a4 -> a5 -> Values b
set5With _ f x1 x2 x3 x4 x5 = set5 f x1 x2 x3 x4 x5

set6 :: (a1 -> a2 -> a3 -> a4 -> a5 -> a6 -> b)
        -> a1 -> a2 -> a3 -> a4 -> a5 -> a6 -> Values b
set6 external

set6With :: Strategy b -> (a1 -> a2 -> a3 -> a4 -> a5 -> a6 -> b)
            -> a1 -> a2 -> a3 -> a4 -> a5 -> a6 -> Values b
set6With _ f x1 x2 x3 x4 x5 x6 = set6 f x1 x2 x3 x4 x5 x6

set7 :: (a1 -> a2 -> a3 -> a4 -> a5 -> a6 -> a7 -> b)
        -> a1 -> a2 -> a3 -> a4 -> a5 -> a6 -> a7 -> Values b
set7 external

set7With :: Strategy b -> (a1 -> a2 -> a3 -> a4 -> a5 -> a6 -> a7 -> b)
            -> a1 -> a2 -> a3 -> a4 -> a5 -> a6 -> a7 -> Values b
set7With _ f x1 x2 x3 x4 x5 x6 x7 = set7 f x1 x2 x3 x4 x5 x6 x7

-- IO selections use the same list as all other Values operations.
getSomeValue :: Values a -> IO (Maybe a)
getSomeValue vs = values2list vs >>= return . first
 where
  first [] = Nothing
  first (x:_) = Just x

getSome :: Values a -> IO (Maybe (a, Values a))
getSome vs = if isEmpty vs then return Nothing else return (Just (select vs))

isEmpty :: Values a -> Bool
isEmpty = Native.isEmpty

notEmpty :: Values a -> Bool
notEmpty = Native.notEmpty

valueOf :: Eq a => a -> Values a -> Bool
valueOf = Native.valueOf

choose :: Eq a => Values a -> (a,Values a)
choose = Native.choose

chooseValue :: Eq a => Values a -> a
chooseValue = Native.chooseValue

select :: Values a -> (a,Values a)
select = Native.select

selectValue :: Values a -> a
selectValue = Native.selectValue

mapValues :: (a -> b) -> Values a -> Values b
mapValues = Native.mapValues

foldValues :: (a -> a -> a) -> a -> Values a -> a
foldValues = Native.foldValues

filterValues :: (a -> Bool) -> Values a -> Values a
filterValues = Native.filterValues

minValue :: Ord a => Values a -> a
minValue = Native.minValue

maxValue :: Ord a => Values a -> a
maxValue = Native.maxValue

minValueBy :: (a -> a -> Ordering) -> Values a -> a
minValueBy = Native.minValueBy

maxValueBy :: (a -> a -> Ordering) -> Values a -> a
maxValueBy = Native.maxValueBy

values2list :: Values a -> IO [a]
values2list = Native.values2list

printValues :: Show a => Values a -> IO ()
printValues = Native.printValues

sortValues :: Ord a => Values a -> [a]
sortValues = Native.sortValues

sortValuesBy :: (a -> a -> Bool) -> Values a -> [a]
sortValuesBy = Native.sortValuesBy
