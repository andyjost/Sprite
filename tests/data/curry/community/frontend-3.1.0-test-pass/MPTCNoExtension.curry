{-# LANGUAGE FunctionalPatterns #-}

module MPTCNoExtension where

import MPTCCoercible

class Coercible a a => IdentityCoerce a where
  idCoerce :: a -> a

instance IdentityCoerce Int where
  idCoerce = coerce

instance IdentityCoerce a => IdentityCoerce [a] where
  idCoerce = map idCoerce

doubleIdentityCoerce :: IdentityCoerce a => a -> a
doubleIdentityCoerce = idCoerce . idCoerce

doubleCoerceWithStep :: (Coercible a b, Coercible b c) => a -> (b, c)
doubleCoerceWithStep x = let y = coerce x in (y, coerce y)

