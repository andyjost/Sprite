{-# LANGUAGE MultiParamTypeClasses, FunctionalDependencies, FlexibleContexts #-}

class C a b | a -> b where
  methodC :: a -> b

-- f :: (C a c, C c b) => a -> b
f = methodC . methodC

-- compose :: (a -> b) -> (b -> c) -> (a -> c)
-- compose f g x = g (f x)

test :: C Int a => a
test = methodC (1 :: Int)
