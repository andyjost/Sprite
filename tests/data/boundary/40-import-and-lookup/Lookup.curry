module Lookup (Item(..), (+++), twice) where

data Item = A | B deriving (Eq, Show)

infixr 5 +++
(+++) :: [a] -> [a] -> [a]
xs +++ ys = xs ++ ys

twice :: Int -> Int
twice n = helper n n

helper :: Int -> Int -> Int
helper a b = a + b
