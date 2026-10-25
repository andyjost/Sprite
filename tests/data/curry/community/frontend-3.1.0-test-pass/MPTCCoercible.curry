{-# LANGUAGE MultiParamTypeClasses, FunctionalPatterns #-}

module MPTCCoercible where

class Coercible a b where
  coerce :: a -> b

instance Coercible Int Int where
  coerce = id

instance Coercible Bool Int where
  coerce False = 0
  coerce True  = 1

instance Coercible Int Bool where
  coerce n | n == 0    = False
           | otherwise = True

instance Coercible a b => Coercible [a] [b] where
  coerce = map coerce

instance (Coercible a c, Coercible b d) => Coercible (a, b) (c, d) where
  coerce (x, y) = (coerce x, coerce y)

uncoerce :: (Coercible b a, Data a, Data b) => a -> b
uncoerce (coerce x) = x
