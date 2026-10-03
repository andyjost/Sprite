module Control.SetFunctions
  (set0, set1, set2, set3, set4, set5, set6, set7
  , Values
  , set, applyS, captureS, evalS, exprS, ($<), ($>), ($##<), ($##>)
  , {--> private -} allValues, valuesOf {- private <--}
  , isEmpty, notEmpty, valueOf
  , choose, chooseValue, select, selectValue, mapValues
  , foldValues, filterValues
  , minValue, minValueBy, maxValue, maxValueBy
  , values2list, printValues, sortValues, sortValuesBy
  ) where

import Data.List ( delete, minimum, minimumBy, maximum, maximumBy, sortBy )

--- Combinators to tranform regular functions into set functions.
set0 :: b -> Values b
set0 external

set1 :: (a1 -> b) -> a1 -> Values b
set1 external

set2 :: (a1 -> a2 -> b) -> a1 -> a2 -> Values b
set2 external

set3 :: (a1 -> a2 -> a3 -> b) -> a1 -> a2 -> a3 -> Values b
set3 external

set4 :: (a1 -> a2 -> a3 -> a4 -> b) -> a1 -> a2 -> a3 -> a4 -> Values b
set4 external

set5 :: (a1 -> a2 -> a3 -> a4 -> a5 -> b)
      -> a1 -> a2 -> a3 -> a4 -> a5 -> Values b
set5 external

set6 :: (a1 -> a2 -> a3 -> a4 -> a5 -> a6 -> b)
      -> a1 -> a2 -> a3 -> a4 -> a5 -> a6 -> Values b
set6 external

set7 :: (a1 -> a2 -> a3 -> a4 -> a5 -> a6 -> a7 -> b)
      -> a1 -> a2 -> a3 -> a4 -> a5 -> a6 -> a7 -> Values b
set7 external

--- Generic set function application.
--- E.g., evalS ((set f) `applyS` a)  -- produces set {f a}.

-- Partial set function appliction.
external data PartialS _

-- Create the set function of a normal function.
set :: a -> PartialS a
set external

-- Create the set function of an expression.
exprS :: a -> PartialS a
exprS external

-- Apply an argument in a set context, excluding its non-determinism.
applyS :: PartialS (a -> b) -> a -> PartialS b
applyS external

($>) :: PartialS (a -> b) -> a -> PartialS b
($>) a b = applyS a b
infixl 0 $>

($##>) :: PartialS (a -> b) -> a -> PartialS b
($##>) f a = (f $>) $## a
infixl 0 $##>

-- Apply an argument in a set context, including its non-determinism.
captureS :: PartialS (a -> b) -> a -> PartialS b
captureS external

($<) :: PartialS (a -> b) -> a -> PartialS b
($<) a b = captureS a b
infixl 0 $<

($##<) :: PartialS (a -> b) -> a -> PartialS b
($##<) f a = (f $<) $## a
infixl 0 $##<

-- Evaluate a set function.
evalS :: PartialS a -> Values a
evalS external


--- Abstract type representing multisets of values.
data Values a = Values [a]

--- Is a multiset of values empty?
isEmpty :: Values a -> Bool
isEmpty (Values vs) = null vs

notEmpty :: Values a -> Bool
notEmpty vs = not (isEmpty vs)

--- Is some value an element of a multiset of values?
valueOf :: Eq a => a -> Values a -> Bool
valueOf e s = e `elem` valuesOf s

--- Chooses (non-deterministically) some value in a multiset of values
--- and returns the chosen value and the remaining multiset of values.
--- Thus, if we consider the operation `chooseValue` by
---
---     chooseValue x = fst (choose x)
---
--- then `(set1 chooseValue)` is the identity on value sets, i.e.,
--- `(set1 chooseValue s)` contains the same elements as the
--- value set `s`.
choose :: Eq a => Values a -> (a,Values a)
choose (Values vs) = (x, Values xs)
  where x = foldr1 (?) vs
        xs = delete x vs

--- Chooses (non-deterministically) some value in a multiset of values
--- and returns the chosen value.
--- Thus, `(set1 chooseValue)` is the identity on value sets, i.e.,
--- `(set1 chooseValue s)` contains the same elements as the
--- value set `s`.
chooseValue :: Eq a => Values a -> a
chooseValue s = fst (choose s)

--- Selects (indeterministically) some value in a multiset of values
--- and returns the selected value and the remaining multiset of values.
--- Thus, `select` has always at most one value.
--- It fails if the value set is empty.
---
--- **NOTE:**
--- The usage of this operation is only safe (i.e., does not destroy
--- completeness) if all values in the argument set are identical.
select :: Values a -> (a,Values a)
select (Values (x:xs)) = (x, Values xs)

--- Selects (indeterministically) some value in a multiset of values
--- and returns the selected value.
--- Thus, `selectValue` has always at most one value.
--- It fails if the value set is empty.
---
--- **NOTE:**
--- The usage of this operation is only safe (i.e., does not destroy
--- completeness) if all values in the argument set are identical.
selectValue :: Values a -> a
selectValue s = fst (select s)

--- Maps a function to all elements of a multiset of values.
mapValues :: (a -> b) -> Values a -> Values b
mapValues f (Values s) = Values (map f s)

--- Accumulates all elements of a multiset of values by applying a binary
--- operation. This is similarly to fold on lists, but the binary operation
--- must be <b>commutative</b> so that the result is independent of the order
--- of applying this operation to all elements in the multiset.
foldValues :: (a -> a -> a) -> a -> Values a -> a
foldValues f z s = foldr f z (valuesOf s)

--- Keeps all elements of a multiset of values that satisfy a predicate.
filterValues :: (a -> Bool) -> Values a -> Values a
filterValues p (Values s) = Values (filter p s)

--- Returns the minimum of a non-empty multiset of values
--- according to the given comparison function on the elements.
minValue :: Ord a => Values a -> a
minValue s = minimum (valuesOf s)

--- Returns the minimum of a non-empty multiset of values
--- according to the given comparison function on the elements.
minValueBy :: (a -> a -> Ordering) -> Values a -> a
minValueBy cmp s = minimumBy cmp (valuesOf s)

--- Returns the maximum of a non-empty multiset of values
--- according to the given comparison function on the elements.
maxValue :: Ord a => Values a -> a
maxValue s = maximum (valuesOf s)

--- Returns the maximum of a non-empty multiset of values
--- according to the given comparison function on the elements.
maxValueBy :: (a -> a -> Ordering) -> Values a -> a
maxValueBy cmp s = maximumBy cmp (valuesOf s)

--- Puts all elements of a multiset of values in a list.
--- Since the order of the elements in the list might depend on
--- the time of the computation, this operation is an I/O action.
values2list :: Values a -> IO [a]
values2list s = return (valuesOf s)

--- Prints all elements of a multiset of values.
printValues :: Show a => Values a -> IO ()
printValues s = values2list s >>= mapM_ print

--- Transforms a multiset of values into a list sorted by
--- the standard term ordering. As a consequence, the multiset of values
--- is completely evaluated.
sortValues :: Ord a => Values a -> [a]
sortValues = sortValuesBy (<=)

--- Transforms a multiset of values into a list sorted by a given ordering
--- on the values. As a consequence, the multiset of values
--- is completely evaluated.
--- In order to ensure that the result of this operation is independent of the
--- evaluation order, the given ordering must be a total order.
sortValuesBy :: (a -> a -> Bool) -> Values a -> [a]
sortValuesBy leq s = sortBy leq (valuesOf s)


------------------------------------------------------------------------
--- Private operations

--- Type representing evaluation of a set function.
external data SetEval _

--- Internal operation to compute all values of a set function.
allValues :: SetEval a -> [a]
allValues external

--- Internal operation to extract all elements of a multiset of values.
valuesOf :: Values a -> [a]
valuesOf (Values s) = s
