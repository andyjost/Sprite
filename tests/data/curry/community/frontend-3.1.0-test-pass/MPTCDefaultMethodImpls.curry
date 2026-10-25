{-# LANGUAGE MultiParamTypeClasses #-}

module MPTCDefaultMethodImpls where

class C a b where
  methodC1, methodC2 :: a -> b -> Bool
  methodC1 x = not . methodC2 x
  methodC2 x = not . methodC1 x

  methodC3 :: (a, b)

  methodC4 :: Either a b
  methodC4 = let (x, y) = methodC3
             in if methodC2 x y then Left x else Right y

instance C Bool Int where
  methodC1 b i = b || i > 0
  methodC3 = (True, -2)

instance C Bool Bool where
  methodC2 b1 b2 = not (b1 || b2)
  methodC3 = (False, True)
  methodC4 = Right False

