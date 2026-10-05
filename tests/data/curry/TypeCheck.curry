-- The module of unit_typecheck.py.  It has type synonyms with and without
-- parameters, a synonym over another synonym, a newtype with a function that
-- unwraps it, a data type with a Num instance, a class with two instances,
-- and functions whose schemes exercise the engine.
module TypeCheck where

import Data.Functor.Identity

type Name = String
type Pair a = (a, a)
type Table k v = [(k, v)]
type Names = [Name]

newtype Wrap a = Wrap a

unwrap :: Wrap a -> a
unwrap (Wrap x) = x

wrapTwice :: a -> Wrap (Wrap a)
wrapTwice x = Wrap (Wrap x)

data Nat = Z | S Nat
  deriving (Eq, Show)

instance Num Nat where
  Z + n = n
  S m + n = S (m + n)
  Z * _ = Z
  S m * n = n + m * n
  negate _ = Z
  abs n = n
  signum Z = Z
  signum (S _) = S Z
  fromInt n = if n <= 0 then Z else S (fromInt (n - 1))

toInt :: Nat -> Int
toInt Z = 0
toInt (S n) = 1 + toInt n

class Pretty a where
  pretty :: a -> String

instance Pretty Bool where
  pretty b = if b then "yes" else "no"

instance Pretty a => Pretty [a] where
  pretty xs = concatMap pretty xs

swap :: Pair a -> Pair a
swap (x, y) = (y, x)

lookupName :: Eq k => k -> Table k v -> Maybe v
lookupName = lookup

runTwice :: Identity (Identity a) -> a
runTwice m = runIdentity (runIdentity m)

twice :: Num a => a -> a
twice x = x + x
