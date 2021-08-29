module Control.SetFunctions
  (set0, set1, set2, set3, set4, set5, set6, set7
  , allValues, valuesOf
  , Values, isEmpty, notEmpty, valueOf
  -- , choose, chooseValue
  -- , select, selectValue
  -- , mapValues
  , foldValues
  -- , filterValues
  -- , minValue, minValueBy, maxValue, maxValueBy
  , values2list, printValues -- , sortValues, sortValuesBy
  ) where

-- import Data.List ( delete, minimum, minimumBy, maximum, maximumBy, sortBy )

external data Values _

allValues :: Values a -> [a]
allValues external

valuesOf :: Values a -> [a]
valuesOf = allValues

isEmpty :: Values a -> Bool
isEmpty vs = case allValues vs of
    []    -> True
    (_:_) -> False

notEmpty :: Values a -> Bool
notEmpty vs = not (isEmpty vs)

valueOf :: Eq a => a -> Values a -> Bool
valueOf e s = e `elem` valuesOf s

-- choose :: Eq a => Values a -> (a,Values a)
-- choose (Values vs) = (x, Values xs)
--   where x = foldr1 (?) vs
--         xs = delete x vs

-- chooseValue :: Eq a => Values a -> a
-- chooseValue s = fst (choose s)

-- select :: Values a -> (a,Values a)
-- select (Values (x:xs)) = (x, Values xs)

-- selectValue :: Values a -> a
-- selectValue s = fst (select s)

-- mapValues :: (a -> b) -> Values a -> Values b
-- mapValues f (Values s) = Values (map f s)

foldValues :: (a -> a -> a) -> a -> Values a -> a
foldValues f z s = foldr f z (valuesOf s)

-- filterValues :: (a -> Bool) -> Values a -> Values a
-- filterValues p (Values s) = Values (filter p s)

-- minValue :: Ord a => Values a -> a
-- minValue s = minimum (valuesOf s)
-- 
-- minValueBy :: (a -> a -> Ordering) -> Values a -> a
-- minValueBy cmp s = minimumBy cmp (valuesOf s)
-- 
-- maxValue :: Ord a => Values a -> a
-- maxValue s = maximum (valuesOf s)
-- 
-- maxValueBy :: (a -> a -> Ordering) -> Values a -> a
-- maxValueBy cmp s = maximumBy cmp (valuesOf s)

values2list :: Values a -> IO [a]
values2list s = return (valuesOf s)

printValues :: Show a => Values a -> IO ()
printValues s = values2list s >>= mapM_ print

-- sortValues :: Ord a => Values a -> [a]
-- sortValues = sortValuesBy (<=)
-- 
-- sortValuesBy :: (a -> a -> Bool) -> Values a -> [a]
-- sortValuesBy leq s = sortBy leq (valuesOf s)

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
