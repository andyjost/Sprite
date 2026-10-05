-- The module of unit_sigtable.py.  It has a class with a default method, an
-- instance without a context and one with a context, a data type, a newtype,
-- functions with one and with two constraints, a binding without a
-- signature, a point-free function, and a private function.
module SigTable
  ( Pretty(..), Shape(..), Age(..), twice, showTwice, unsigned, prettyMaybe
  ) where

class Pretty a where
  pretty :: a -> String
  prettyList :: [a] -> String
  prettyList xs = concatMap pretty xs

data Shape = Circle Float | Rect Float Float

instance Pretty Shape where
  pretty (Circle r) = "circle " ++ show r
  pretty (Rect w h) = "rect " ++ show w ++ " " ++ show h

instance Pretty a => Pretty (Maybe a) where
  pretty Nothing = "nothing"
  pretty (Just x) = pretty x

newtype Age = Age Int

twice :: Num a => a -> a
twice x = x + x

showTwice :: (Show a, Num a) => a -> String
showTwice x = show (twice x)

unsigned = Just 5

prettyMaybe :: Maybe Shape -> String
prettyMaybe = pretty

hidden :: Int -> Int
hidden x = x + 1
