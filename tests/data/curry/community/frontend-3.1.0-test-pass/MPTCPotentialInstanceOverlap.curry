{-# LANGUAGE MultiParamTypeClasses #-}

module MPTCPotentialInstanceOverlap where

class C a b c where
  methodC :: a -> b -> c -> Bool

instance C [a] [a] [b] where
  methodC _ _ _ = True

instance C [a] [b] [b] where
  methodC _ _ _ = False

f1 :: C a a b => a -> b -> Bool
f1 x = methodC x x

f2 x = let b = methodC [True] [x] [5 :: Int] in b && x

-- The following function is accepted, just like in Haskell, even though it
-- could be considered to require activating a FlexibleContexts language
-- extension.
f3 x z = let f' y = methodC x y z
         in (f' [True] || f' [5 :: Int]) : x ++ map (> (0 :: Int)) z

-- Expected result: True
testExp1 :: Bool
testExp1 = methodC [True] [True] [[]]

-- Expected result: False
testExp2 :: Bool
testExp2 = methodC [True] [5 :: Int] [5 :: Int]

-- Expected result: True
testExp3 :: Bool
testExp3 = f1 [5 :: Int] [True]

-- Expected result: False
testExp4 :: Bool
testExp4 = f2 False

-- Expected result: [True, False, True, True, False]
testExp5 :: [Bool]
testExp5 = f3 [False, True] [42, -17]
