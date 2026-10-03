-- Newtype declarations and uses, which the first pass eliminates, together
-- with an imported newtype, a type synonym ahead of a data declaration, and
-- class instances for the newtype.
module Newtypes where

import Data.Functor.Identity

type Name = String

newtype Wrap a = Wrap { unwrap :: a }
  deriving (Eq, Show)

data Shape = Circle Float | Square Float | Named Name (Wrap Int)

newtype Age = Age Int

instance Eq Age where
  Age a == Age b = a == b

instance Ord Age where
  compare (Age a) (Age b) = compare a b

instance Functor Wrap where
  fmap f (Wrap a) = Wrap (f a)

wrapAll :: [a] -> [Wrap a]
wrapAll = map Wrap

wrapOne :: Int -> Wrap Int
wrapOne n = Wrap (n + 1)

unwrapCase :: Wrap Int -> Int
unwrapCase w = case w of
  Wrap n -> n + 1

unwrapComplex :: Int -> Int
unwrapComplex n = case wrapOne n of
  Wrap m -> m * 2

unwrapField :: Wrap Int -> Int
unwrapField w = unwrap w

ageSum :: [Age] -> Int
ageSum as = foldr (+) 0 [ a | Age a <- as ]

older :: Age -> Age -> Age
older a b = if a < b then b else a

ident :: Int -> Int
ident n = runIdentity (Identity n)

identMap :: Int -> Identity Int
identMap n = fmap (+ 1) (Identity n)

identCase :: Identity Int -> Int
identCase i = case i of
  Identity n -> n

area :: Shape -> Float
area s = case s of
  Circle r -> 3.0 * r * r
  Square a -> a * a
  Named _ (Wrap n) -> fromInt n
