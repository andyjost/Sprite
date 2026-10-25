{-# LANGUAGE MultiParamTypeClasses #-}

module MPTCNullaryClasses where

class C where
  methodC :: Bool

class C => D where
  methodD :: a -> a -> Bool

class D => E where
  methodE :: Bool
  methodE = methodC && methodD True True

class E => F where
  methodF :: Bool

instance C where
  methodC = True

instance D where
  methodD _ _ = methodC

f1 :: D => Int -> Bool
f1 = methodD 5

f2 :: E => Bool
f2 = methodE

f3 :: F => Bool
f3 = let f3'  _ = methodF
         f3'' _ = methodE
         f3''' :: E => () -> Bool
         f3''' _ = methodE
     in f3' () && f3'' () & f3''' ()

-- Expected result: True
testExp1 :: Bool
testExp1 = f1 4

-- Expected result: True
testExp2 :: Bool
testExp2 = methodC
