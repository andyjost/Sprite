{-# LANGUAGE FunctionalDependencies #-}
module FunDepImpliesMPTC where

class C a b where
  f :: a -> b
