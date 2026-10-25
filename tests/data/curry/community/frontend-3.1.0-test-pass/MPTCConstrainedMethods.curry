{-# LANGUAGE MultiParamTypeClasses #-}

module MPTCConstrainedMethods where

class C a b c where
  methodC1 :: D => a -> b -> c
  methodC2 :: E d => a -> b -> c -> d
  methodC3 :: C a d e => a -> b -> c -> d -> e
  methodC4 :: F a b c d => a -> b -> c -> d

class D

instance D

class E a where
  methodE :: a

class F a b c d where
  methodF :: a -> b -> c -> d

instance C Bool Bool Bool where
  methodC1 _ _ = True
  methodC2 _ _ _ = methodE
  methodC3 a _ _ d = methodC1 a d
  methodC4 = methodF


instance C Bool Int Bool where
  methodC1 _ _ = False
  methodC2 _ _ _ = methodE
  methodC3 a _ _ = methodC1 a
  methodC4 = methodF

