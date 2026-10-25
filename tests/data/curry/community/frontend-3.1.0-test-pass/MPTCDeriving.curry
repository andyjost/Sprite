{-# LANGUAGE MultiParamTypeClasses #-}

module MPTCDeriving where

class C a b where
  showAB :: a -> b -> String

data Foo a b = Foo a b

instance C a b => Show (Foo a b) where
  show (Foo x y) = "(Foo " ++ showAB x y ++ ")"

data Bar a b = Bar (Foo a b)
  deriving Show

showBar :: C a b => Bar a b -> String
showBar = show

instance C Bool Char where
  showAB b c = show b ++ ' ' : show c

instance C a b => C (a, b) (b, a) where
  showAB (x1, x2) (y1, y2) =
    '(' : showAB x1 y1 ++ ", " ++ reverse (showAB y2 x2) ++ ")"

instance C (a, b) (a, b) where
  showAB _ _ = "error"

data Baz = Baz (Foo (Bool, Char) (Char, Bool))
  deriving Show

-- Expected result: "Bar (Foo False 'f')"
testExp1 :: String
testExp1 = show (Bar (Foo False 'f'))

-- Expected result: "Baz (Foo (True 'b', 'a' eslaF))"
testExp2 :: String
testExp2 = show (Baz (Foo (True, 'a') ('b', False)))
